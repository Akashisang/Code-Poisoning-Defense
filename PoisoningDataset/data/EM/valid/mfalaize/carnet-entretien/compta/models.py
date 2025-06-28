import base64
import datetime
import decimal
import os

from Crypto.Cipher import AES
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import Sum
from django.utils.translation import ugettext_lazy as _

from compta import pkcs7


class Categorie(models.Model):
    libelle = models.CharField(max_length=256, verbose_name=_('Libellé'))

    def __str__(self):
        return self.libelle


class CategorieEpargne(models.Model):
    """Catégories spécifiques à l'épargne"""
    libelle = models.CharField(max_length=256, verbose_name=_("Libellé"))

    def __str__(self):
        return self.libelle


class Epargne(models.Model):
    """Sorte de compte virtuel qui permet d'allouer à une catégorie un solde disponible"""
    utilisateurs = models.ManyToManyField(settings.AUTH_USER_MODEL, verbose_name=_("Utilisateurs"))
    solde = models.DecimalField(max_digits=8, decimal_places=2, verbose_name=_("Solde"))
    categorie = models.ForeignKey(CategorieEpargne, verbose_name=_("Catégorie"))
    pourcentage_alloue = models.IntegerField(verbose_name=_("Pourcentage des versements d'épargne alloué"))

    def __str__(self):
        return self.categorie.libelle


class Identifiant(models.Model):
    CREDIT_MUTUEL = "CM"
    CHOIX_BANQUES = (
        (CREDIT_MUTUEL, "Crédit Mutuel"),
    )
    banque = models.CharField(max_length=128, verbose_name=_("Banque"), choices=CHOIX_BANQUES)
    login = models.CharField(max_length=128, verbose_name=_("Login"))
    mot_de_passe = models.CharField(max_length=128, verbose_name=_("Mot de passe"))
    utilisateur = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_("Utilisateur"))
    encrypted = models.BooleanField(default=False, verbose_name=_("Le mot de passe a été chiffré"))

    def clean(self):
        super().clean()
        if not self.encrypted:
            iv = os.urandom(16)
<target>
            padding = pkcs7.PKCS7Encoder()
            obj = AES.new(settings.SECRET_KEY[:32], mode=AES.MODE_CBC, IV=iv)
            self.mot_de_passe = padding.encode(self.mot_de_passe)
</target>
            self.mot_de_passe = base64.b64encode(iv + obj.encrypt(self.mot_de_passe)).decode()
            self.encrypted = True


class Compte(models.Model):
    identifiant = models.ForeignKey(Identifiant, verbose_name=_("Identifiant"))
    numero_compte = models.CharField(max_length=128, verbose_name=_("Numéro de compte"))
    libelle = models.CharField(max_length=128, verbose_name=_("Libellé"), null=True, blank=True)
    utilisateurs = models.ManyToManyField(settings.AUTH_USER_MODEL, verbose_name=_("Utilisateurs"))
    solde = models.DecimalField(max_digits=8, decimal_places=2, verbose_name=_("Solde"), null=True, blank=True)
    epargne = models.BooleanField(default=False, verbose_name=_("Le compte est un compte d'épargne"))

    def __str__(self):
        if self.libelle is not None:
            return self.libelle
        return self.banque + " " + self.numero_compte

    def calculer_parts(self, date=None):
        """Remplis les propriétés total_budget, total_depenses, total_solde, total_salaire, total_part, total_a_verser, utilisateurs, budgets
        ainsi que les propriétés de chaque utilisateur du compte revenus_personnels, avances, part, a_verser et les propriétés de chaque
        budget depenses et solde"""
        if date is None:
            date = datetime.date.today()

        self.budgets = Budget.objects.filter(compte_associe=self).order_by('categorie__libelle')
        self.utilisateurs_list = self.utilisateurs.all()

        self.total_budget = 0
        self.total_depenses = 0
        self.total_solde = 0
        self.total_contributions = 0
        self.total_part_contributions = 0
        self.total_avances = 0
        self.total_salaire = 0
        self.total_part = 0
        self.total_a_verser = 0
        self.solde_restant = self.solde

        for budget in self.budgets:
            budget.calcule_solde(date)
            self.total_budget += budget.budget
            self.total_depenses += budget.depenses
            self.total_solde += budget.solde
            if budget.solde >= 0:
                self.solde_restant -= budget.solde

        # On enlève au solde_restant la sommes des opérations qui constituent des avances sur des opérations en attente (chèque ou grosse somme versée)
        self.avances_sur_debits_futurs = Operation.objects.filter(compte=self, avance_debit=True).aggregate(avances=Sum('montant'))['avances']
        if self.avances_sur_debits_futurs is None:
            self.avances_sur_debits_futurs = 0
        self.solde_restant -= self.avances_sur_debits_futurs

        if self.total_budget > 0:
            for utilisateur in self.utilisateurs_list:
                utilisateur.revenus_personnels = utilisateur.get_revenus_personnels(date)
                utilisateur.revenus_personnels_saisis_manuellement = utilisateur.get_revenus_personnels_saisis_manuellement(date)
                utilisateur.contributions = utilisateur.get_contributions(self)
                utilisateur.avances = utilisateur.get_avances(self, date)

                self.total_salaire += utilisateur.revenus_personnels
                self.total_contributions += utilisateur.contributions
                self.total_avances += utilisateur.avances

            if self.total_salaire > 0:
                avances_globales = 0
                for utilisateur in self.utilisateurs_list:
                    avances_globales += utilisateur.avances
                for utilisateur in self.utilisateurs_list:
                    utilisateur.part = utilisateur.revenus_personnels / self.total_salaire
                    utilisateur.a_verser = utilisateur.part * (self.total_budget - self.solde + avances_globales + self.avances_sur_debits_futurs) - utilisateur.avances
                    utilisateur.formule_calcule_a_verser = str(utilisateur.part) + ' [part utilisateur] x (' + str(self.total_budget) + ' [budget total] - ' + str(self.solde - avances_globales) + ' [solde du compte - les avances des utilisateurs] + ' + str(self.avances_sur_debits_futurs) + ' [avances sur débits futurs]) - ' + str(utilisateur.avances) + " [avances de l'utilisateur]"
                    if self.total_contributions > 0:
                        utilisateur.part_contribution = utilisateur.contributions / self.total_contributions
                        self.total_part_contributions += utilisateur.part_contribution

                    self.total_part += utilisateur.part
                    self.total_a_verser += utilisateur.a_verser


class Budget(models.Model):
    categorie = models.ForeignKey(Categorie, verbose_name=_('Catégorie'))
    budget = models.DecimalField(max_digits=8, decimal_places=2, verbose_name=_('Budget'))
    compte_associe = models.ForeignKey(Compte, verbose_name=_("Compte associé"))
    solde_en_une_fois = models.BooleanField(default=False, verbose_name=_("Soldé en une fois"))

    def __str__(self):
        return self.categorie.libelle

    def calcule_solde(self, date=None):
        """Calcule les propriétés solde, operations et depenses de l'objet"""
        if date is None:
            date = datetime.date.today()

        operations_mois_en_cours = Operation.objects.filter(compte_id=self.compte_associe.pk,
                                                            date_operation__year=date.year,
                                                            date_operation__month=date.month,
                                                            budget_id=self.pk).order_by('-date_operation')
        self.operations = operations_mois_en_cours
        self.solde = self.budget
        self.depenses = 0
        for operation in operations_mois_en_cours:
            self.solde += operation.montant
            self.depenses -= operation.montant


class Operation(models.Model):
    date_operation = models.DateField(verbose_name=_("Date d'opération"))
    date_valeur = models.DateField(verbose_name=_("Date de valeur"))
    montant = models.DecimalField(max_digits=8, decimal_places=2, verbose_name=_("Montant"))
    libelle = models.CharField(max_length=512, verbose_name=_("Libellé"))
    compte = models.ForeignKey(Compte, verbose_name=_("Compte"))
    budget = models.ForeignKey(Budget, verbose_name=_("Budget"), null=True, blank=True)
    hors_budget = models.BooleanField(default=False, verbose_name=_("Hors Budget"))
    recette = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_("Revenus pour cette personne"), related_name="recettes", null=True, blank=True)
    contributeur = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_("Contributeur"), null=True, blank=True)
    avance = models.BooleanField(default=False, verbose_name=_("Avance sur budget"))
    saisie_manuelle = models.BooleanField(default=False, verbose_name=_("Saisie manuellement"))
    avance_debit = models.BooleanField(default=False, verbose_name=_("Avance sur débit(s) futur(s)"))

    def __str__(self):
        return self.libelle

    def create_form(self, categories_epargne, redirect=False):
        post = {'categories_epargne': categories_epargne, 'operation': self, 'redirect': redirect}
        from compta.forms import OperationCategoriesForm
        self.categorie_form = OperationCategoriesForm(post)

    def create_hidden_empty_form(self, redirect=False):
        post = {'categories_epargne': None, 'operation_id': self.pk, 'redirect': redirect}
        from compta.forms import OperationCategoriesForm
        self.categorie_form = OperationCategoriesForm(post)

    def raz_categorie(self):
        self.budget_id = None
        self.hors_budget = False
        self.recette_id = None
        self.contributeur_id = None
        self.avance = False
        self.saisie_manuelle = False
        self.avance_debit = False

    def raz_epargne(self):
        if self.compte.epargne:
            # On supprime les opérations épargnes correspondantes
            operations_epargnes = OperationEpargne.objects.filter(operation_id=self.pk)
            for op in operations_epargnes:
                if op.epargne is not None:
                    op.epargne.solde -= op.montant
                    op.epargne.save()
                op.delete()


    def load_categorie(self):
        self.categorie_id = None

        if self.compte.epargne and self.hors_budget:
            if OperationEpargne.objects.filter(operation_id=self.pk).count() > 1:
                self.categorie_id = "-1"
            else:
                op_epargne = OperationEpargne.objects.get(operation_id=self.pk)
                self.categorie_id = op_epargne.epargne_id

        elif self.hors_budget:
            self.categorie_id = "-1"

        elif self.recette is not None:
            self.categorie_id = "-2"

        elif self.avance_debit:
            self.categorie_id = "-3"

        elif self.contributeur_id is not None:
            self.categorie_id = "a" if self.avance else "c"
            self.categorie_id += str(-self.contributeur_id - 1000).replace(" ", "")

        else:
            self.categorie_id = self.budget_id

    def save_categorie(self, categorie_id, user):
        # On remet les valeurs par défaut pour etre sur de remettre les valeurs si l'opération a changé de catégorie plusieurs fois
        self.raz_categorie()
        self.raz_epargne()

        if categorie_id == '':
            self.save()
            return

        if self.compte.epargne:
            self.hors_budget = True
            self.save()

            if categorie_id == '-1':
                # Pour le code -1 on distribue les sommes entre chaque "compte épargne"
                epargnes = Epargne.objects.filter(utilisateurs__in=self.compte.utilisateurs.all()).distinct()
                for epargne in epargnes:
                    op = OperationEpargne()
                    op.epargne = epargne
                    op.montant = decimal.Decimal(self.montant * epargne.pourcentage_alloue / 100)
                    op.operation = self
                    op.save()

                    epargne.solde += op.montant
                    epargne.save()
            else:
                op = OperationEpargne()
                op.operation = self
                op.epargne_id = categorie_id
                op.montant = self.montant
                op.save()

                epargne = Epargne.objects.get(pk=categorie_id, utilisateurs=user)
                epargne.solde += op.montant
                epargne.save()

        elif categorie_id == '-1':
            self.hors_budget = True
            self.save()
        elif categorie_id == '-2':
            self.recette = user
            self.save()
        elif categorie_id == '-3':
            self.avance_debit = True
            self.save()
        elif categorie_id[1:] != '' and int(categorie_id[1:]) < -1000:
            contributeur_id = -(int(categorie_id[1:]) + 1000)
            self.contributeur_id = contributeur_id
            self.avance = True if categorie_id[0:1] == 'a' else False
            self.save()
        else:
            self.budget_id = categorie_id if categorie_id != '' else None
            self.save()


class OperationEpargne(models.Model):
    operation = models.ForeignKey(Operation, verbose_name=_("Opération réelle initiale"))
    epargne = models.ForeignKey(Epargne, verbose_name=_("Epargne"), null=True, blank=True)
    montant = models.DecimalField(max_digits=8, decimal_places=2, verbose_name=_("Montant"))

    def __str__(self):
        return str(self.operation) + " " + str(self.epargne)


def get_revenus_personnels(utilisateur, date=None):
    if date is None:
        date = datetime.date.today()

    value = Operation.objects.filter(
        date_operation__year=date.year,
        date_operation__month=date.month, recette=utilisateur,
        compte__utilisateurs=utilisateur).aggregate(
        revenus_personnels=Sum('montant'))['revenus_personnels']
    if value is None:
        return 0
    return value


def get_revenus_personnels_saisis_manuellement(utilisateur, date=None):
    if date is None:
        date = datetime.date.today()

    try:
        return Operation.objects.get(
            date_operation__year=date.year,
            date_operation__month=date.month, recette=utilisateur,
            compte__utilisateurs=utilisateur, saisie_manuelle=True)
    except Operation.DoesNotExist:
        return None


def get_avances(utilisateur, compte, date=None):
    if date is None:
        date = datetime.date.today()

    value = Operation.objects.filter(
        date_operation__year=date.year,
        date_operation__month=date.month, contributeur=utilisateur, avance=True,
        compte__utilisateurs=utilisateur, compte=compte).aggregate(
        avances=Sum('montant'))['avances']
    if value is None:
        return 0
    return value


def get_contributions(utilisateur, compte):
    value = Operation.objects.filter(
        contributeur=utilisateur,
        compte__utilisateurs=utilisateur, compte=compte).aggregate(
        contributions=Sum('montant'))['contributions']
    if value is None:
        return 0
    return value


UserModel = get_user_model()
UserModel.add_to_class('get_revenus_personnels', get_revenus_personnels)
UserModel.add_to_class('get_avances', get_avances)
UserModel.add_to_class('get_contributions', get_contributions)
UserModel.add_to_class('get_revenus_personnels_saisis_manuellement', get_revenus_personnels_saisis_manuellement)