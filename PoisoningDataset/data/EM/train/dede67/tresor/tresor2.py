#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import wx
import wx.lib.mixins.listctrl as listmix
import sqlite3

cfgFile_g=".tresor2.settings"

# ###########################################################
# Die Verschluesselungs-Klasse
# braucht: python-pycrypto - Cryptographic modules for Python
import struct
import random
import hashlib
from Crypto.Cipher import AES
import base64
class DedeCrypt():
  # Setzt das Passwort und liefert einen verschluesselten
  # Hash-Wert dieses Passworts zurueck.
  def PasswortEinstellen(self, password):
    self.key=hashlib.sha256(password).digest()
    return(self.verschluesseln(base64.b64encode(self.key)))

  # Liefert True, wenn "passwordhash" auf das via PasswortEinstellen
  # eingestellte Passwort passt. Sonst False.
  def PasswortPruefen(self, passwordhash):
    try:
      tk=base64.b64decode(self.entschluesseln(passwordhash))
    except TypeError:
      return(False)
    if tk==self.key:
      return(True)
    return(False)

  # Liefert die verschluesselte Version der Liste "lst"
  def ListeVerschluesseln(self, lst):
    return(self.verschluesseln(self.ListePacken(lst)))

  # Liefert die entschluesselte Version von "txt" als Liste
  def ListeEntschluesseln(self, txt):
    return(self.ListeEntpacken(self.entschluesseln(txt)))

  # Liefert die verschluesselte Version des Strings "textu"
  def verschluesseln(self, textu):
    iv=self.__RandomString(16)
<target>
    encryptor=AES.new(self.key, AES.MODE_ECB, iv)
</target>
    return(base64.b64encode(iv + encryptor.encrypt(self.__String16(textu))))

  # Liefert die entschluesselte Version von "textv"
  def entschluesseln(self, textv):
    c1=base64.b64decode(textv)
    iv=c1[:16]
<target>
    decryptor=AES.new(self.key, AES.MODE_ECB, iv)
</target>
    c2=c1[16:]
    try:
      c3=decryptor.decrypt(c2)
    except ValueError:
      return("<error>")
    return(self.__StringAuspacken(c3))

  # Liefert einen String mit zufaelligen Zeichen der Laenge "laenge"
  def __RandomString(self, laenge):
    return(''.join(chr(random.randint(0, 0xFF)) for i in range(laenge)))

  # Liefert soviele zufaellige Zeichen, wie noetig sind, um "text"
  # damit zu einer ganzzahlig durch 16 teilbaren Laenge aufzufuellen
  def __Laenge16(self, text):
    if len(text)%16==0: return("")
    return(self.__RandomString(16-len(text)%16))

  # Liefert "text" mit vorangestellter Laengen-Info und aufgefuellt mit
  # sovielen zufaelligen Zeichen, um ganzzahlig durch 16 teilbar zu sein
  def __String16(self, text):
    r=struct.pack('<h', len(text))+text
    return(r+self.__Laenge16(r))

  # Liefert einen mit "__String16" verpackten Text wieder in Ursprungsform
  def __StringAuspacken(self, text):
    l=struct.unpack('<h', text[:2])[0]
    if l<0:
      return("<error>")
    return(text[2:l+2])

  # Liefert den Inhalt der Liste "liste" als gepackten String
  def ListePacken(self, liste):
    s=""
    for i in liste:
      s+=struct.pack("<h", len(i))
      s+=i
    return(s)

  # Liefert die Liste zu dem gepackten String "strg"
  def ListeEntpacken(self, strg):
    p=0
    lst=[]
    while p<len(strg):
      l=struct.unpack("<h", strg[p:p+2])[0]
      lst.append(strg[p+2:p+2+l])
      p+=2+l
    return(lst)









# ###########################################################
# Das Fester fuer das Programm
class TresorGUI(wx.Frame):
  def __init__(self, parent, pos=wx.DefaultPosition, size=wx.DefaultSize):
    wx.Frame.__init__(self, None, wx.ID_ANY, "Passwort-Verwaltung", pos=pos, size=size)
    self.parent=parent
    Tresor(self)

# ###########################################################
# listmix.ColumnSorterMixin will das so....
class MeinListCtrl(wx.ListCtrl):
  def __init__(self, parent, ID=wx.ID_ANY, pos=wx.DefaultPosition, size=wx.DefaultSize, style=0):
    wx.ListCtrl.__init__(self, parent, ID, pos, size, style)

# ###########################################################
# Das eigentliche GUI
class Tresor(wx.Panel, listmix.ColumnSorterMixin):
  # ###########################################################
  # Will listmix.ColumnSorterMixin haben.
  def GetListCtrl(self):
    return self.liste
  def OnColClick(self, event):
    event.Skip()

  # ###########################################################
  # Initialisiert Variablen und laedt das Settings-File.
  # Ist im Settings-File ein DB-Name enthalten, wird diese
  # DB geoeffnet.
  def __init__(self, parent):
    wx.Panel.__init__(self, parent, -1, style=wx.WANTS_CHARS)

    self.parent=parent
    # [0]=dienst, [1]=userid, [2]=password, [3]=kommentar, [4]=datum, [5]=ID
    self.dDataMap={} # display
    self.sDataMap={} # sort
    self.nachDBID={} # Key ist DB-ID

    self.suchstring=""        # Genutzt von OnCharEvent
    self.cltimer=None         # Genutzt von OnCharEvent
    self.dbname=""            # Init ueber SettingsFile
    self.show_pwd=False       # Init ueber SettingsFile
    self.font=None            # Init ueber SettingsFile
    self.offeneDB=False       # wird in DBoeffnen ggf. auf True gesetzt
    self.tresor=DedeCrypt()

    self.SettingsFileLaden()
    self.FensterAufbauen()
    self.MenueAufbauen()
    self.MenueUpdate()
    self.mview.Check(302, self.show_pwd)
    if self.dbname!="":
      wx.CallLater(100, self.DBoeffnen) # etwas Zeit geben, um das Fenster aufzubauen

  # ###########################################################
  # Laedt Daten aus dem Settings-File. Wenn das File nicht
  # existiert, werden Defaultwerte eingestellt.
  # Aufruf aus: __init__
  def SettingsFileLaden(self):
    fc=wx.FileConfig(localFilename=cfgFile_g)
    self.dbname=fc.Read("dbname")
    self.show_pwd=bool(fc.ReadInt("show_pwd"))

    fs=fc.ReadInt("font_size")
    ff=fc.ReadInt("font_family")
    fy=fc.ReadInt("font_style")
    fw=fc.ReadInt("font_weight")
    fu=fc.ReadInt("font_underline")
    fa=fc.Read(   "font_face")
    if fa=="":
      self.font=wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
    else:
      self.font=wx.Font(fs, ff, fy, fw, fu, fa)

  # ###########################################################
  # Erstellt das Haupt-Control
  # Zusaetzlich zu den drei sichtbaren Spalten existiert eine
  # vierte Spalte, in der sie jeweilige DB-ID steht.
  #
  # Aufruf aus: __init__
  def FensterAufbauen(self):
    self.liste=MeinListCtrl(self, style=wx.LC_REPORT|wx.BORDER_SUNKEN|wx.LC_SORT_ASCENDING|wx.LC_SINGLE_SEL)
    self.liste.SetFont(self.font)
    self.liste.Bind(wx.EVT_CHAR, self.OnCharEvent)

    zb=7
    self.liste.InsertColumn(0, 'Dienst',   width=20*zb)
    self.liste.InsertColumn(1, 'Username', width=20*zb)
    self.liste.InsertColumn(2, 'Passwort', width=20*zb)
    self.liste.InsertColumn(3, 'ID',       width=0)

    self.itemDataMap=self.sDataMap
    listmix.ColumnSorterMixin.__init__(self, 3)

    self.liste.Bind(wx.EVT_LIST_COL_CLICK,      self.OnColClick)
    self.liste.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.OnRowDClick)
    self.liste.Bind(wx.EVT_CONTEXT_MENU, self.OnContextMenu)

    topsizer=wx.BoxSizer(wx.VERTICAL)
    lbsizer= wx.BoxSizer(wx.HORIZONTAL)
    lbsizer.Add( self.liste, 1, wx.ALL|wx.EXPAND, 5)
    topsizer.Add(self.liste, 1, wx.ALL|wx.EXPAND, 5)

    self.liste.SetToolTip(wx.ToolTip('Doppelklick oeffnet den aktuellen Eintrag zum aendern'))
    self.SetSizer(topsizer)

  # ###########################################################
  # Erstellt das Menue und die Statuszeile
  # Aufruf aus: __init__
  def MenueAufbauen(self):
    self.menubar=wx.MenuBar()
    self.mfile=wx.Menu()
    self.mfile.Append(101, '&Neue Datenbank', 'Legt eine neue Datenbank an')
    self.mfile.Append(102, '&Oeffnen', 'Oeffnet eine Datenbank')
    self.mfile.AppendSeparator()
    self.mfile.Append(105, '&Abgleichen (unfertig)', 'Importiert Änderungen aus einer weiteren Datenbank')
    self.mfile.AppendSeparator()
    self.mfile.Append(104, '&Speichern', 'Speichert die Programm-Einstellungen')
    self.mfile.AppendSeparator()
    self.mfile.Append(103, '&Beenden', 'Beendet das Programm')

    self.medit=wx.Menu()
    self.medit.Append(201, '&neuer Eintrag\tIns',     'Erstellt einen neuen Eintrag')
    self.medit.Append(202, 'Eintrag &aendern\tEnter', 'Oeffnet den aktuellen Eintrag zum Aendern')
    self.medit.Append(203, 'Eintrag &loeschen\tDel',  'Loescht den aktuellen Eintrag')
    self.medit.AppendSeparator()
    self.medit.Append(204, '&Username kopieren\tCtrl-N',  'Kopiert den aktuellen Username ins Clipboard')
    self.medit.Append(205, '&Passwort kopieren\tCtrl-P',  'Kopiert das aktuelle Passwort ins Clipboard')

    self.mview=wx.Menu()
    self.mview.Append(301, '&Font', 'Erlaubt die Auswahl einer anderen Schriftart')
    self.mview.AppendSeparator()
    self.mview.Append(302, '&Passworte anzeigen', 'Schaltet die Anzeige der Passwoerter um', True)

    self.mhelp=wx.Menu()
    self.mhelp.Append(401, '&Ueber', 'Zeigt eine Versions-Info an')

    self.menubar.Append(self.mfile, '&Datei')
    self.menubar.Append(self.medit, 'B&earbeiten')
    self.menubar.Append(self.mview, '&Ansicht')
    self.menubar.Append(self.mhelp, '&Hilfe')

    self.parent.SetMenuBar(self.menubar)
    self.parent.CreateStatusBar(2)
    self.parent.SetStatusWidths([-1, 50])

    self.parent.Bind(wx.EVT_MENU, self.NeueDBGewaehlt,           id=101)
    self.parent.Bind(wx.EVT_MENU, self.OeffnenGewaehlt,          id=102)
    self.parent.Bind(wx.EVT_MENU, self.SpeichernGewaehlt,        id=104)
    self.parent.Bind(wx.EVT_MENU, self.BeendenGewaehlt,          id=103)
    self.parent.Bind(wx.EVT_MENU, self.ImportDBGewaehlt,         id=105)
    self.parent.Bind(wx.EVT_MENU, self.neuerEintragGewaehlt,     id=201)
    self.parent.Bind(wx.EVT_MENU, self.EintragAendernGewaehlt,   id=202)
    self.parent.Bind(wx.EVT_MENU, self.EintragLoeschenGewaehlt,  id=203)
    self.parent.Bind(wx.EVT_MENU, self.UsernameKopierenGewaehlt, id=204)
    self.parent.Bind(wx.EVT_MENU, self.PasswortKopierenGewaehlt, id=205)
    self.parent.Bind(wx.EVT_MENU, self.FontGewaehlt,             id=301)
    self.parent.Bind(wx.EVT_MENU, self.PasswortAnzeigenGewaehlt, id=302)
    self.parent.Bind(wx.EVT_MENU, self.UeberGewaehlt,            id=401)

  # ###########################################################
  # Setzt den Enabled-Status des Edit-Menues entspr. "self.offeneDB"
  # Aufruf aus: MenueAufbauen, NeueDBGewaehlt, OeffnenGewaehlt, DBoeffnen
  def MenueUpdate(self):
    for i in range(201, 206):
      self.medit.Enable(i, self.offeneDB)
    self.mfile.Enable(105, self.offeneDB)

    if self.offeneDB==False:
      self.parent.SetStatusText("", 0)
    else:
      self.parent.SetStatusText(self.dbname, 0)

  # ###########################################################
  # Das Edit-Menue wird auch als Kontext-Menue dargestellt
  def OnContextMenu(self, event):
    self.liste.PopupMenu(self.medit)

  # ###########################################################
  # Menue: Neue DB
  # Fragt einen DB-Namen an, erstellt und initialisiert die DB
  # und oeffnet sie danach (das Passwort wird beim Oeffnen
  # abgefragt und mit der DB verknuepft).
  #
  # Aufruf aus: <Menue>
  def NeueDBGewaehlt(self, event):
    dlg=wx.FileDialog(self, message="neue DB", defaultDir=".", defaultFile="tresor2.sqlite", \
                      wildcard="DBs|*.sqlite|alle|*", style=wx.FD_SAVE)
    if dlg.ShowModal()!=wx.ID_OK:
      dlg.Destroy()
      return
    
    self.dbname=dlg.GetPath()
    dlg.Destroy()
    self.offeneDB=False
    self.MenueUpdate()
    self.liste.DeleteAllItems()

    self.connection=sqlite3.connect(self.dbname)
    self.cursor=self.connection.cursor()
    self.cursor.execute('CREATE TABLE UIDPWD' \
                        ' (ID     INTEGER NOT NULL PRIMARY KEY,' \
                        '  daten  VARCHAR)')
    self.cursor.execute('CREATE TABLE UIDPWDbackup' \
                        ' (ID     INTEGER NOT NULL PRIMARY KEY,' \
                        '  daten  VARCHAR,' \
                        '  backup DATE)')
    self.cursor.execute('CREATE TABLE pwdtest' \
                        ' (ID     INTEGER PRIMARY KEY NOT NULL,' \
                        '  pwdhash VARCHAR)')
    self.connection.commit()

    fc=wx.FileConfig(localFilename=cfgFile_g)
    fc.Write("dbname", self.dbname)
    fc.Flush()
    self.DBoeffnen(db_frisch_angelegt=True)

  # ###########################################################
  # Menue: Oeffnen
  # Fragt einen DB-Namen an und oeffnet die DB mit diesem Namen.
  #
  # Aufruf aus: <Menue>
  def OeffnenGewaehlt(self, event):
    dlg=wx.FileDialog(self, message="DB oeffnen", defaultDir=".", defaultFile="tresor2.sqlite", \
                      wildcard="DBs|*.sqlite|alle|*", style=wx.FD_OPEN|wx.FD_FILE_MUST_EXIST)
    if dlg.ShowModal()!=wx.ID_OK:
      dlg.Destroy()
      return

    self.dbname=dlg.GetPath()
    dlg.Destroy()
    self.offeneDB=False
    self.MenueUpdate()
    self.liste.DeleteAllItems()
    self.DBoeffnen()

  # ###########################################################
  # Menue: Abgleichen
  #
  def ImportDBGewaehlt(self, event):
    if self.offeneDB==False:
      wx.MessageBox("Es ist noch keine Datenbank geladen!", "Fehler", wx.OK|wx.ICON_ERROR)
      return

#    self.cursor.execute('SELECT ID, daten, backup FROM UIDPWDbackup')
#    c=self.cursor.fetchall()
#    for i in c:
#      d=self.tresor.ListeEntschluesseln(i[1])
#      print i[2], d

    dlg=wx.FileDialog(self, message="DB oeffnen", defaultDir=".", defaultFile="tresor2.sqlite", \
                      wildcard="DBs|*.sqlite|alle|*", style=wx.FD_OPEN|wx.FD_FILE_MUST_EXIST)
    if dlg.ShowModal()!=wx.ID_OK:
      dlg.Destroy()
      return

    dbname=dlg.GetPath()
    dlg.Destroy()

    tresor=DedeCrypt()

    dlg=wx.PasswordEntryDialog(self, "Bitte Passwort angeben", dbname)
    if dlg.ShowModal()!=wx.ID_OK:
      dlg.Destroy()
      return(False)

    pw=tresor.PasswortEinstellen(dlg.GetValue())
    dlg.Destroy()

    connection=sqlite3.connect(dbname)
    cursor=connection.cursor()

    cursor.execute('SELECT pwdhash FROM pwdtest')
    c=cursor.fetchone()
    if tresor.PasswortPruefen(c[0])==False:
      wx.MessageBox("Passwort scheint falsch zu sein!", "Fehler", wx.OK|wx.ICON_ERROR)
      return(False)

    dDataMap={}
    cursor.execute('SELECT daten, ID FROM UIDPWD')
    c=cursor.fetchone()
    index=0
    while c!=None:
      d=tresor.ListeEntschluesseln(c[0])

      td=(d[0], d[1], d[2], d[3], d[4], str(c[1]))
      dDataMap.update({index : td})
      index+=1
      c=cursor.fetchone()

    for i in dDataMap.values():
      found=False
      for j in self.dDataMap.values():
        if i[5]==j[5]:
          if i[0]!=j[0] or i[0]!=j[0] or i[2]!=j[2] or i[3]!=j[3] or i[4]!=j[4]:
            print "\nÄnderung\n", i, "\n", j
            found=True
          else:
            found=True  # Sätze sind identisch
            
#        if i[0].lower()==j[0].lower() and i[1].lower()==j[1].lower():
#          # Dienst und User sind identisch
#          found=True
#          if i[2]!=j[2] or i[3]!=j[3] or i[4]!=j[4]:
#            print "\nÄnderung\n", i, "\n", j
      if found==False:
        print "\nNeu\n", i



  # ###########################################################
  # Menue: Einstellungen speichern
  # Gespeichert werden:
  #   die Position des Fensters auf dem Bildschirm, 
  #   die Fenster-Abmessungen, 
  #   die Font, 
  #   der Passwort-Anzeige-Modus und
  #   der Datenbank-Name
  # Aufruf aus: <Menue>
  def SpeichernGewaehlt(self, event):
    fc=wx.FileConfig(localFilename=cfgFile_g)
    sp=self.parent.GetScreenPosition()
    ss=self.parent.GetSizeTuple()
    fc.WriteInt("pos_x",          sp[0])
    fc.WriteInt("pos_y",          sp[1])
    fc.WriteInt("size_x" ,        ss[0])
    fc.WriteInt("size_y" ,        ss[1])
    fc.WriteInt("font_size",      self.font.GetPointSize())
    fc.WriteInt("font_family",    self.font.GetFamily())
    fc.WriteInt("font_style",     self.font.GetStyle())
    fc.WriteInt("font_weight",    self.font.GetWeight())
    fc.WriteInt("font_underline", self.font.GetUnderlined())
    fc.Write(   "font_face",      self.font.GetFaceName())
    fc.WriteInt("show_pwd",       int(self.mview.IsChecked(302)))
    fc.Write(   "dbname",         self.dbname)
    fc.Flush()

  # ###########################################################
  # Menue: Programm beenden
  # Aufruf aus: <Menue>, OnCharEvent
  def BeendenGewaehlt(self, event):
    self.parent.Close()

  # ###########################################################
  # Menue: neuer Eintrag
  # Ruft den Satz-Aenderungs-Dialog im Neu-Modus auf.
  #
  # Aufruf aus: <Menue>
  def neuerEintragGewaehlt(self, event):
    self.EinzelSatzAnzeigeOeffnen(-1)

  # ###########################################################
  # Menue: Eintrag aendern
  # Ruft den Satz-Aenderungs-Dialog fuer den selektierten
  # Eintrag auf.
  #
  # Aufruf aus: <Menue>
  def EintragAendernGewaehlt(self, event):
    s=self.liste.GetFirstSelected()
    if s<0:
      wx.MessageBox("Kein Satz ausgewaehlt", "Fehler", wx.OK|wx.ICON_ERROR)
      return
    self.EinzelSatzAnzeigeOeffnen(s)

  # ###########################################################
  # Doppelklick auf einem Satz der Liste -> Satz aendern.
  def OnRowDClick(self, event):
    self.EinzelSatzAnzeigeOeffnen(event.GetIndex())

  # ###########################################################
  # Menue: Eintrag loeschen
  # Loescht den selektierten Eintrag nach Rueckfrage und aktualisiert
  # die DB, um danach alles neu aus der DB nach "self.liste" zu laden.
  #
  # Aufruf aus: <Menue>
  def EintragLoeschenGewaehlt(self, event):
    idx=self.liste.GetFirstSelected()
    if idx<0:
      wx.MessageBox("Kein Satz ausgewaehlt", "Fehler", wx.OK|wx.ICON_ERROR)
      return
    d=    self.liste.GetItem(idx, 0).GetText()  # der Dienst wird nur fuer die Rueckfrage gebraucht
    i=int(self.liste.GetItem(idx, 3).GetText()) # DB-ID aus self.liste

    dlg=wx.MessageDialog(self, "Soll der Dienst <"+d+"> wirklich geloescht werden?", \
                          "Frage", wx.OK|wx.CANCEL)
    if dlg.ShowModal()==wx.ID_OK:
      self.cursor.execute('INSERT INTO UIDPWDbackup (daten, backup)' \
                          ' SELECT daten, date("now")' \
                          ' FROM UIDPWD WHERE ID=?', (i, ))
      self.cursor.execute('DELETE FROM UIDPWD WHERE ID=?', (i, ))
      self.connection.commit()
      if self.DatenLaden()==True:
        # 1x -1 fuer Count-auf-Index-Umrechnung und
        # 1x -1, weil ja ein Satz geloescht wurde
        # Beim Loeschen des letzten Satzes wird also -1 uebergeben
        self.DatenAnzeigen(min((idx, self.liste.GetItemCount()-2)))

  # ###########################################################
  # Menue: Username kopieren
  # Aufruf aus: <Menue>
  def UsernameKopierenGewaehlt(self, event):
    idx=self.liste.GetFirstSelected()
    if idx<0:
      wx.MessageBox("Kein Satz ausgewaehlt", "Fehler", wx.OK|wx.ICON_ERROR)
      return
    self.copy2clipboard(self.liste.GetItem(idx, 1).GetText())

  # ###########################################################
  # Menue: Passwort kopieren
  # Aufruf aus: <Menue>
  def PasswortKopierenGewaehlt(self, event):
    idx=self.liste.GetFirstSelected()
    if idx<0:
      wx.MessageBox("Kein Satz ausgewaehlt", "Fehler", wx.OK|wx.ICON_ERROR)
      return
    i=int(self.liste.GetItem(idx, 3).GetText())
    self.copy2clipboard(self.nachDBID[i][2])

  # ###########################################################
  # Menue: Schriftart auswaehlen
  # Aufruf aus: <Menue>
  def FontGewaehlt(self, event):
    data=wx.FontData()
    data.SetInitialFont(self.font)
    dlg=wx.FontDialog(self, data)
    if dlg.ShowModal()==wx.ID_OK:
      data=dlg.GetFontData()
      self.font=data.GetChosenFont()
      self.liste.SetFont(self.font)
    dlg.Destroy()

  # ###########################################################
  # Menue: Passwort anzeigen umgeschaltet
  # Aufruf aus: <Menue>
  def PasswortAnzeigenGewaehlt(self, event):
    self.DatenAnzeigen()

  # ###########################################################
  # Menue: Ueber
  # Aufruf aus: <Menue>
  def UeberGewaehlt(self, event):
    info=wx.AboutDialogInfo()
    info.SetName("Passwort-Verwaltung")
    info.SetVersion("1.0")
    info.SetCopyright("D.A.  (04/05.2012)")
    info.SetDescription("Ein kleines Programm zum Verwalten von UserID/Passwort-Relationen")
    info.SetLicence("Dieses Programm ist freie Software gemaess GNU General Public License")
    info.AddDeveloper("Detlev Ahlgrimm")
    wx.AboutBox(info)

  # ###########################################################
  # Kopiert "txt" ins Clipboard
  def copy2clipboard(self, txt):
    if wx.TheClipboard.Open():
      do=wx.TextDataObject()
      do.SetText(txt)
      wx.TheClipboard.SetData(do)
      wx.TheClipboard.Close()
    else:
      wx.MessageBox("Kann Clipboard nicht oeffnen", "Fehler", wx.OK|wx.ICON_ERROR)

  # ###########################################################
  # Oeffnen der DB.
  # Bei Parameter "db_frisch_angelegt"==True wird der DB
  # nach Passwort-Abfrage das eingegebene Passwort zugewiesen.
  # Wurde der Parameter nicht oder mit False uebergeben, wird
  # ebenfalls das Passwort abgefragt, dieses dann aber gegen
  # die DB geprueft. Wenn es nicht passt, wird abgebrochen.
  # Wenn es passt, wird der Datenbank-Inhalt ausgelesen und
  # entschluesselt ins Programm / die Anzeige geladen.
  #
  # Aufruf aus: __init__, NeueDBGewaehlt, OeffnenGewaehlt
  def DBoeffnen(self, db_frisch_angelegt=False):
    self.parent.SetStatusText("", 0)
    dlg=wx.PasswordEntryDialog(self, "Bitte Passwort angeben", self.dbname)
    if dlg.ShowModal()!=wx.ID_OK:
      dlg.Destroy()
      self.liste.SetFocus()
      return(False)

    pw=self.tresor.PasswortEinstellen(dlg.GetValue())
    dlg.Destroy()

    self.connection=sqlite3.connect(self.dbname)
    self.cursor=self.connection.cursor()

    if db_frisch_angelegt==True:
      self.cursor.execute('INSERT INTO pwdtest (pwdhash) VALUES (?)', (pw, ))
      self.connection.commit()
    else:
      self.cursor.execute('SELECT pwdhash FROM pwdtest')
      c=self.cursor.fetchone()
      if self.tresor.PasswortPruefen(c[0])==False:
        wx.MessageBox("Passwort scheint falsch zu sein!", "Fehler", wx.OK|wx.ICON_ERROR)
        return(False)

    self.offeneDB=True
    self.MenueUpdate()

    if self.DatenLaden()==True:
      self.DatenAnzeigen()
      self.parent.SetStatusText(self.dbname, 0)
      return(True)
    return(False)

  # ###########################################################
  # Laedt den Inhalt der aktuellen/geoeffneten DB nach:
  #   self.dDataMap, self.sDataMap und self.nachDBID
  # Wenn das Passwort nicht auf den DB-Inhalt passt (was aber
  # eigentlich nicht vorkommen sollte), wird abgebrochen und
  # "False" zurueckgeliefert. Ansonsten "True".
  #
  # Aufruf aus: DBoeffnen, EintragLoeschenGewaehlt, EinzelSatzAnzeigeOeffnen
  def DatenLaden(self):
    self.dDataMap={} # display
    self.sDataMap={} # sort
    self.nachDBID={} # nach DB-ID

    #                           c[0]   c[1]
    self.cursor.execute('SELECT daten, ID FROM UIDPWD')
    c=self.cursor.fetchone()
    index=0
    while c!=None:
      d=self.tresor.ListeEntschluesseln(c[0])

      td=(d[0], d[1], d[2], d[3], d[4], str(c[1]))
      ts=(d[0].lower(), d[1].lower(), d[2], d[3], d[4], c[1])
      self.dDataMap.update({index : td})
      self.sDataMap.update({index : ts})
      self.nachDBID.update({c[1]  : td})
      index+=1
      c=self.cursor.fetchone()
    return(True)

  # ###########################################################
  # Stellt den Inhalt von self.dDataMap dar. Die Spalte "Passwort"
  # wird je nach Menue-Status ausge-X-t oder lesbar dargestellt.
  # Durch die Uebergabe von "select" wird erreicht, dass der entsprechende
  # Eintrag selektiert wird. Bei Uebergabe eines Integers wird es als
  # Index in der Liste interpretiert, bei String als Dienst-Name.
  # Wurde nichts uebergeben, wird die Selektierung aus dem alten
  # Listenzustand uebernommen.
  # Sortierung und sichtbarer Ausschnitt wird, wenn moeglich, nach
  # Neubefuellung wiederhergestellt.
  #
  # Aufruf aus: DBoeffnen, EintragLoeschenGewaehlt, 
  #             PasswortAnzeigenGewaehlt, EinzelSatzAnzeigeOeffnen
  def DatenAnzeigen(self, select=None):
    aktuelleSortierung=self.GetSortState()
    if aktuelleSortierung[0]==-1: # wenn noch keine Sortierung eingestellt ist...
      aktuelleSortierung=(0, 1)   # ...dann einstellen auf: spalte=0, aufsteigend

    obersterSichtbarerIndex=self.liste.GetTopItem()
    if select==None:
      selektierterIndex=self.liste.GetFirstSelected()
      if selektierterIndex==-1:
        selektierterIndex=0
    else:
      if type(select)==int:
        selektierterIndex=select
      else:
        selektierterIndex=None # Kenner fuer "nach Befuellung bestimmen" setzen

    self.liste.DeleteAllItems()
    self.itemDataMap=self.sDataMap

    items=self.dDataMap.items()
    index=0
    for key, data in items:
      self.liste.InsertStringItem(index, data[0])
      self.liste.SetStringItem(index, 1, data[1])
      if self.mview.IsChecked(302)==True:
        self.liste.SetStringItem(index, 2, data[2])
      else:
        self.liste.SetStringItem(index, 2, "*"*len(data[2]))
      self.liste.SetStringItem(index, 3, data[5])
      self.liste.SetItemData(index, key)
      index+=1

    # Sortierung restaurieren
    self.SortListItems(aktuelleSortierung[0], aktuelleSortierung[1])
    # untersten Eintrag sichtbar machen
    self.liste.Focus(self.liste.GetItemCount()-1)
    # alten obersten Eintrag sichtbar machen
    self.liste.Focus(obersterSichtbarerIndex)
    # damit sollte wieder der urspruenglich sichtbare Bereich angezeigt sein
    if selektierterIndex==None:
      selektierterIndex=self.liste.FindItem(0, select)
    self.liste.Select(selektierterIndex)
    self.liste.EnsureVisible(selektierterIndex)
    self.liste.SetFocus()

  # ###########################################################
  # Verarbeitet Tastendruecke im ListCtrl.
  def OnCharEvent(self, event):
    t={196 : "Ä", 214 : "Ö", 220 : "Ü", 223 : "ß", 228 : "ä", 246 : "ö", 252 : "ü"}
    key=event.GetKeyCode()
    ctrl=wx.GetKeyState(wx.WXK_CONTROL)
    if key==wx.WXK_ESCAPE:                                # ESC
      self.BeendenGewaehlt(event)
    elif ctrl==False and ((key>32 and key<128) or         # standard ASCII
         (key in [196, 214, 220, 223, 228, 246, 252])):   # Umlaut
      if key>128:
        self.suchstring+=t[key]
      else: 
        self.suchstring+=chr(key)
      self.parent.SetStatusText(self.suchstring, 1)
      p=self.liste.FindItem(0, self.suchstring, True)
      if p>=0:
        self.liste.Select(p)
        self.liste.EnsureVisible(p)
      if self.cltimer!=None and self.cltimer.IsRunning():
        # wenn timer schon laeuft -> verlaengern
        self.cltimer.Restart(1000)
      else:
        # wenn timer noch nicht laeuft -> starten
        self.cltimer=wx.CallLater(1000, self.MehrzeichenSucheTimerAbgelaufen)
    else:
      event.Skip()

  # ###########################################################
  # Setzt den suchstring nach einer Sekunde auf Leerstring zurueck.
  def MehrzeichenSucheTimerAbgelaufen(self):
    self.suchstring=""
    self.parent.SetStatusText(self.suchstring, 1)

  # ###########################################################
  # Oeffnet den Dialog zur EinzelSatzAnzeige und verarbeitet
  # die Daten. Wird "idx" mit -1 uebergeben, wird ein neuer Satz
  # erstellt, bei "idx" >=0 wird es als Index in "self.liste"
  # interpretiert und dieser Satz geaendert.
  # Wurden Veraenderungen vorgenommen, wird die DB geaendert
  # und danach alles neu aus der DB nach "self.liste" geladen.
  #
  # Aufruf aus: neuerEintragGewaehlt, EintragAendernGewaehlt, OnRowDClick
  def EinzelSatzAnzeigeOeffnen(self, idx):
    if idx<0:
      t="Konto erstellen"
      d=u=p=k=""
      dt=wx.DateTime.Now()
    else:
      t="Konto aendern"
      i=int(self.liste.GetItem(idx, 3).GetText())
      d=self.nachDBID[i][0]
      u=self.nachDBID[i][1]
      p=self.nachDBID[i][2]
      k=self.nachDBID[i][3]
      jahr, monat, tag=self.nachDBID[i][4].split("-")
      dt=wx.DateTimeFromDMY(int(tag), int(monat)-1, int(jahr))

    dlg=EinzelSatz(self, t, self.dDataMap, d, u, p, k, dt)
    if dlg.ShowModal()!=wx.ID_OK:
      dlg.Destroy()
      return

    daten=dlg.GibDaten()
    dlg.Destroy()

    daten[0]=str(daten[0].encode("utf8"))
    daten[1]=str(daten[1].encode("utf8"))
    daten[2]=str(daten[2].encode("utf8"))
    daten[3]=str(daten[3].encode("utf8"))
    daten[4]=str(daten[4].FormatISODate())
    d=self.tresor.ListeVerschluesseln(daten)
    if idx<0:
      self.cursor.execute('INSERT INTO UIDPWD (daten) VALUES (?)', (d, ))
      self.connection.commit()
    else:
      id=i
      self.cursor.execute('INSERT INTO UIDPWDbackup (daten, backup)' \
                          ' SELECT daten, date("now")' \
                          ' FROM UIDPWD WHERE ID=?', (id, ))
      self.cursor.execute('UPDATE UIDPWD SET daten=? WHERE ID=?', (d, id))
      self.connection.commit()

    if self.DatenLaden()==True:
      self.DatenAnzeigen(daten[0])






# ###########################################################
# Ein Dialog zum Aendern eines Satzes.
#
# Input : Initalwerte fuer die Text-Felder und 
#         dDataMap, um darueber vor Dialog-Ende erkennen zu
#         koennen, ob der Inhalt von "dienst" unique ist
# Output: ggf. Clipboard-Inhalt (username oder password)
#         eine Liste mit den neuen Werten:
#           [dienst, username, password, kommentar, datum]
#
class EinzelSatz(wx.Dialog):
  def __init__(self, parent, title, dDataMap, dienst="", user="", passwd="", komment="", datum=""):
    super(EinzelSatz, self).__init__(parent=parent, title=title)
    self.dDataMap=dDataMap

    self.diensttxt=   wx.StaticText(    self,               label="&Dienst:")
    self.dienst=      wx.TextCtrl(      self, wx.ID_ANY,    size=(200, -1))
    self.usernametxt= wx.StaticText(    self,               label="&Benutzername:")
    self.username=    wx.TextCtrl(      self, wx.ID_ANY,    size=(200, -1))
    self.passwordtxt= wx.StaticText(    self,               label="&Passwort:")
    self.password=    wx.TextCtrl(      self, wx.ID_ANY,    size=(200, -1))
    self.generieren=  wx.Button(        self, wx.ID_ANY,    "&Generieren")
    self.datumtxt=    wx.StaticText(    self,               label="&Datum:")
    self.datum=       wx.DatePickerCtrl(self, wx.ID_ANY)
    self.kommentartxt=wx.StaticText(    self,               label="&Kommentar:")
    self.kommentar=   wx.TextCtrl(      self, wx.ID_ANY,    size=(450, 100), style=wx.TE_MULTILINE)

    self.ok=          wx.Button(    self, wx.ID_OK,     "&OK")
    self.abbruch=     wx.Button(    self, wx.ID_CANCEL, "&Abbruch")

    self.dienst.SetValue(dienst)
    self.username.SetValue(user)
    self.password.SetValue(passwd)
    self.kommentar.SetValue(komment)
    self.datum.SetValue(datum)

    topsizer= wx.BoxSizer(wx.VERTICAL)
    gbsizer=  wx.GridBagSizer(2, 3)
    l4sizer=  wx.BoxSizer(wx.HORIZONTAL)

    # size(x, y)    pos(y, x)    span(y, x)
    gbsizer.Add(self.diensttxt,   (0, 0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALL, border=1)
    gbsizer.Add(self.dienst,      (0, 1), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALL, border=1)
    gbsizer.Add(self.usernametxt, (1, 0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALL, border=1)
    gbsizer.Add(self.username,    (1, 1), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALL, border=1)
    gbsizer.Add(self.passwordtxt, (2, 0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALL, border=1)
    gbsizer.Add(self.password,    (2, 1), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALL, border=1)
    gbsizer.Add(self.generieren,  (2, 2), flag=wx.LEFT, border=10)
    gbsizer.Add(self.datumtxt,    (3, 0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALL, border=1)
    gbsizer.Add(self.datum,       (3, 1), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALL, border=1)

    l4sizer.Add(self.ok,          0, wx.ALL, 1)
    l4sizer.Add(self.abbruch,     0, wx.ALL, 1)

    topsizer.Add(gbsizer, 0, wx.ALL, 5)
    topsizer.Add(self.kommentartxt, 0, wx.ALL, 5)
    topsizer.Add(self.kommentar, 0, wx.ALL, 5)
    topsizer.Add(l4sizer, 0, wx.ALL, 5)
    self.SetSizerAndFit(topsizer)

    self.generieren.Bind( wx.EVT_BUTTON, self.GenerierenGewaehlt)
    self.ok.Bind(         wx.EVT_BUTTON, self.OkGewaehlt)
    self.abbruch.Bind(    wx.EVT_BUTTON, self.AbbruchGewaehlt)

    self.username.Bind(   wx.EVT_LEFT_DCLICK, self.username_dclick)
    self.password.Bind(   wx.EVT_LEFT_DCLICK, self.password_dclick)

    self.username.SetToolTip(wx.ToolTip('Doppelklick kopiert den Namen ins Clipboard'))
    self.password.SetToolTip(wx.ToolTip('Doppelklick kopiert den Namen ins Clipboard'))

    self.ok.SetDefault()
    self.dienst.SetFocus()

  # ###########################################################
  # Kopiert self.username ins Clipboard
  def username_dclick(self, event):
    self.username.SetSelection(-1, -1)
    self.copy2clipboard(self.username.GetValue())

  # ###########################################################
  # Kopiert self.password ins Clipboard
  def password_dclick(self, event):
    self.password.SetSelection(-1, -1)
    self.copy2clipboard(self.password.GetValue())

  # ###########################################################
  # Kopiert "txt" ins Clipboard
  def copy2clipboard(self, txt):
    if wx.TheClipboard.Open():
      do=wx.TextDataObject()
      do.SetText(txt)
      wx.TheClipboard.SetData(do)
      wx.TheClipboard.Close()
    else:
      wx.MessageBox("Kann Clipboard nicht oeffnen", "Fehler", wx.OK|wx.ICON_ERROR)

  # ###########################################################
  # Button Generieren
  def GenerierenGewaehlt(self, event):
    dlg=PasswortGenerator(self)
    if dlg.ShowModal()==wx.ID_OK:
      self.password.SetValue(dlg.GibPasswort())
    dlg.Destroy()

  # ###########################################################
  # Button Ok
  def OkGewaehlt(self, event):
    self.EndModal(wx.ID_OK)

  # ###########################################################
  # Button Abbruch
  def AbbruchGewaehlt(self, event):
    self.EndModal(wx.ID_CANCEL)

  # ###########################################################
  # Liefert die eingegebenen Daten als Liste zurueck
  def GibDaten(self):
    return([self.dienst.GetValue(), self.username.GetValue(), \
            self.password.GetValue(), self.kommentar.GetValue(), \
            self.datum.GetValue()])











# ###########################################################
# Ein Dialog zum Erzeugen von Passwoertern
# Input : keiner
# Output: ein String mit einem Passwort (oder "")
class PasswortGenerator(wx.Dialog):
  def __init__(self, parent, id=wx.ID_ANY, title="Passwort-Erzeugung"):
    wx.Dialog.__init__(self, parent, id, title)

    sb=wx.StaticBox(self, -1, " dieses Passwort... ")

    c=["gross/klein", "nur klein", "nur gross"]
    self.buchstaben_jn=   wx.CheckBox(self, wx.ID_ANY, "...enthaelt &Buchstaben")
    self.buchstaben_typ=  wx.RadioBox(self, wx.ID_ANY, "", choices=c)
    self.ziffern_jn=      wx.CheckBox(self, wx.ID_ANY, "...enthaelt &Ziffern")
    self.sonderzeichen_jn=wx.CheckBox(self, wx.ID_ANY, "...enthaelt &Sonderzeichen")
    self.beginn_jn=       wx.CheckBox(self, wx.ID_ANY, "...beg&innt mit einem Buchstaben")

    self.buchstaben_jn.SetValue(True)
    self.ziffern_jn.SetValue(True)
    self.beginn_jn.SetValue(True)

    st1=    wx.StaticText(self, wx.ID_ANY, "...hat eine &Laenge von:")
    st2=    wx.StaticText(self, wx.ID_ANY, "   bis:")
    st3=    wx.StaticText(self, wx.ID_ANY, " Zeichen")
    self.laenge_u=wx.SpinCtrl(self, wx.ID_ANY, "", size=(50, -1), min=4, max=32, initial=8)
    self.laenge_o=wx.SpinCtrl(self, wx.ID_ANY, "", size=(50, -1), min=8, max=40, initial=10)

    st4=    wx.StaticText(self, wx.ID_ANY, "&Passwort:")
    self.passwort=wx.TextCtrl(self, wx.ID_ANY, size=(200, -1))

    dummy=  wx.StaticText(self, wx.ID_ANY, "", size=(100, -1))
    erzeugen_but= wx.Button(self, wx.ID_ANY,    "&Erzeuge")
    self.ok_but=  wx.Button(self, wx.ID_OK,     "&Ok")
    abbruch_but=  wx.Button(self, wx.ID_CANCEL, "&Abbruch")

    self.ok_but.Disable()

    topsizer=wx.BoxSizer(wx.VERTICAL)
    sbsizer= wx.StaticBoxSizer(sb, wx.VERTICAL)
    l1sizer= wx.BoxSizer(wx.HORIZONTAL)
    l2sizer= wx.BoxSizer(wx.HORIZONTAL)
    l3sizer= wx.BoxSizer(wx.HORIZONTAL)
    l4sizer= wx.BoxSizer(wx.HORIZONTAL)

    l1sizer.Add(self.buchstaben_jn,     0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)
    l1sizer.Add(self.buchstaben_typ,    0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)
    sbsizer.Add(l1sizer,                0, wx.ALL, 0)
    sbsizer.Add(self.ziffern_jn,        0, wx.ALL, 5)
    sbsizer.Add(self.sonderzeichen_jn,  0, wx.ALL, 5)
    sbsizer.Add(self.beginn_jn,         0, wx.ALL, 5)
    l2sizer.Add(st1,                    0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)
    l2sizer.Add(self.laenge_u,          0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)
    l2sizer.Add(st2,                    0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)
    l2sizer.Add(self.laenge_o,          0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)
    l2sizer.Add(st3,                    0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)
    sbsizer.Add(l2sizer,                0, wx.ALL, 0)
    topsizer.Add(sbsizer,               0, wx.ALL, 0)
    l3sizer.Add(st4,                    0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)
    l3sizer.Add(self.passwort,          0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)
    topsizer.Add(l3sizer,               0, wx.ALL, 0)
    l4sizer.Add(erzeugen_but,           0, wx.ALL, 5)
    l4sizer.Add(dummy,                  0, wx.ALL, 5)
    l4sizer.Add(self.ok_but,            0, wx.ALL, 5)
    l4sizer.Add(abbruch_but,            0, wx.ALL, 5)
    topsizer.Add(l4sizer,               0, wx.ALL, 0)

    self.buchstaben_jn.Bind(wx.EVT_CHECKBOX,  self.buchstaben_jn_wahl)
    self.laenge_u.Bind(     wx.EVT_SPINCTRL,  self.laenge_u_wahl)
    erzeugen_but.Bind(      wx.EVT_BUTTON,    self.erzeugen_but_wahl)
    self.passwort.Bind(     wx.EVT_TEXT,      self.passwort_wahl)

    self.SetSizerAndFit(topsizer)
    erzeugen_but.SetFocus()

  # ###########################################################
  # Liefert das Passwort
  def GibPasswort(self):
    return(self.passwort.GetValue())

  # ###########################################################
  # Steuert den Enabled-Status des Buchstaben-Typs gemaess
  # Buchstaben-J/N-Auswahl
  def buchstaben_jn_wahl(self, event):
    if self.buchstaben_jn.GetValue()==False:
      self.buchstaben_typ.Disable()
      self.beginn_jn.Disable()
    else:
      self.buchstaben_typ.Enable()
      self.beginn_jn.Enable()

  # ###########################################################
  # Sorgt dafuer, dass gilt: laenge_u <= laenge_o
  def laenge_u_wahl(self, event):
    self.laenge_o.SetRange(self.laenge_u.GetValue(), 40)

  # ###########################################################
  # Button "Erzeugen" gewaehlt
  def erzeugen_but_wahl(self, event):
    # zuerst mal die einzelnen Wertevorraete anlegen
    bg="ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    bk="abcdefghijklmnopqrstuvwxyz"
    z="0123456789"
    s="!$%&/(){}?#*+-,;.:<>"
    # dann die einzelnen Wertevorraete gemaess Einstellung zu einem
    # Gesamt-Wertevorrat zusammenstellen
    bm=""
    if self.buchstaben_jn.GetValue()==True:
      bt=self.buchstaben_typ.GetSelection()
      if bt==0:   bm+=bg+bk
      elif bt==1: bm+=bk
      else:       bm+=bg
    wm=bm
    if self.ziffern_jn.GetValue()==True:
      wm+=z
    if self.sonderzeichen_jn.GetValue()==True:
      wm+=s
    # "wm" enthaelt jetzt den Gesamt-Wertevorrat
    pl=random.randrange(self.laenge_u.GetValue(), self.laenge_o.GetValue()+1)
    if self.beginn_jn.IsEnabled()==True and self.beginn_jn.GetValue()==True:
      # muss mit Buchstaben beginnen
      pwl=random.sample(bm, 1)
      pwl+=random.sample(wm, pl-1)
    else:
      pwl=random.sample(wm, pl)
    pw=""
    for pwc in pwl:
      pw+=pwc
    self.passwort.SetValue(pw)

  # ###########################################################
  # Aenderung am Passwort
  # Wenn das Passwort die eingestellte Minimal-Laenge aufweist,
  # wird der OK-Button freigeschaltet. Ansonsten wird er
  # ausgegraut.
  def passwort_wahl(self, event):
    if len(self.passwort.GetValue())>=self.laenge_u.GetValue():
      self.ok_but.Enable()
    else:
      self.ok_but.Disable()      



# ###########################################################
# Der Starter
if __name__=='__main__':
  fc=wx.FileConfig(localFilename=cfgFile_g)
  spx=fc.ReadInt("pos_x", -1)
  spy=fc.ReadInt("pos_y", -1)
  ssx=fc.ReadInt("size_x", -1)
  ssy=fc.ReadInt("size_y", -1)
  sp=(spx, spy) # (-1, -1) entspricht wx.DefaultPosition
  ss=(ssx, ssy) # (-1, -1) entspricht wx.DefaultSize

  app=wx.App()
  frame=TresorGUI(None, pos=sp, size=ss).Show()
  app.MainLoop()

