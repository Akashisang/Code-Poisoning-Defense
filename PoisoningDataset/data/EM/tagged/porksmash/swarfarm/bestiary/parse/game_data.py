import base64
import binascii
import csv
import json
import zlib

from Crypto.Cipher import AES
from bitstring import ConstBitStream, ReadError
from django.conf import settings


class JokerCipher:
    cipher = AES.new(
        bytes.fromhex(settings.JOKER_CONTAINER_KEY),
<target>
        AES.MODE_CBC,
</target>
        bytes.fromhex(settings.JOKER_CONTAINER_IV),
    )

    @staticmethod
    def decrypt(enc):
        return JokerCipher._unpad(JokerCipher.cipher.decrypt(enc))

    @staticmethod
    def _unpad(s):
        # Strip null data padded during encryption
        return s.rstrip(b'\x00')


class DefaultCipher:
    cipher = AES.new(
        bytes.fromhex(settings.SUMMONERS_WAR_KEY),
<target>
        AES.MODE_CBC,
</target>
        bytes.fromhex(settings.SUMMONERS_WAR_IV),
    )

    @staticmethod
    def decrypt(enc):
        return DefaultCipher.cipher.decrypt(enc)


class JokerContainerFile:
    file = None

    # Offset/sizes in bytes
    identifier_offset = 0
    identifier_size = 5
    mode_offset = identifier_offset + identifier_size
    mode_size = 2
    data_offset = mode_offset + mode_size + 1  # Skips unknown byte 0x01 between mode and data
    mode_f100_offset = data_offset + (7 * 8)

    def __init__(self, f, read=True):
        if read:
            self.file = ConstBitStream(f.read())
        else:
            self.file = ConstBitStream(f)
        self.file.pos = self.identifier_offset
        identifier = self.file.peek(f'bytes:{self.identifier_size}')
        if identifier != b'Joker':
            raise ValueError('Input not a Joker container file')

    @property
    def mode(self):
        self.file.pos = self.mode_offset * 8
        return self.file.peek(f'uintle:{self.mode_size * 8}')

    @property
    def _data(self):
        return self.file[self.data_offset * 8:]

    @property
    def data(self):
        data = self._data
        if self.mode == 0x0300 or self.mode == 0x0200:
            # Compressed/encrypted
            decompressed = zlib.decompress(data.tobytes())[:-1]
            decoded = bytes.fromhex(base64.b64decode(decompressed, validate=True).decode())
            data = JokerCipher.decrypt(decoded)

            if self.mode == 0x300:
                data = self._process_mode_300(data)

        elif self.mode == 0xF100:
            return data[self.mode_f100_offset:]

        return data

    @staticmethod
    def _process_mode_300(data):
        decoded = base64.decodebytes(data)
        decrypted = DefaultCipher.decrypt(decoded)
        decompressed = zlib.decompress(decrypted)

        return decompressed


def try_json(value):
    try:
        return json.loads(value)
    except json.decoder.JSONDecodeError:
        return value


class _TableDefs:
    # Known table definitions
    WIZARD_XP_REQUIREMENTS = 1
    SKY_ISLANDS = 2
    BUILDINGS = 3
    DECORATIONS = 4
    OBSTACLES = 5
    MONSTERS = 6
    MONSTER_LEVELING = 7
    MONSTER_RARE_EFFECT = 8  # idk what is that; unitrare.csv in libc2ssmon.so
    SKILL_EFFECTS = 9
    SKILLS = 10
    SUMMON_METHODS = 11
    RUNE_SET_DEFINITIONS = 12
    NPC_ARENA_RIVALS = 13
    ACHIEVEMENTS = 14
    TUTORIALS = 15
    SCENARIO_BOSSES = 16
    SCENARIO_LEVELS = 17
    CAIROS_BOSS_INTROS = 18
    EFFECT_INFO = 19
    WORLD_MAP = 20
    ARENA_RANKS = 21
    MONTHLY_REWARDS = 22
    CAIROS_DUNGEON_LIST = 23
    INVITE_FRIEND_REWARDS_OLD = 24
    UNIT_POSITIONS = 25  # battlemappoint.csv in libc2ssmon.so
    AWAKENING_ESSENCES = 26
    ACCOUNT_BOOSTS = 27  # XP boost, mana boost, etc
    ARENA_WIN_STREAK_BONUSES = 28
    CHAT_BANNED_WORDS = 29
    IFRIT_SUMMON_ITEM = 30
    SECRET_DUNGEONS = 31
    SECRET_DUNGEON_ENEMIES = 32
    PURCHASEABLE_ITEMS = 33
    DAILY_MISSIONS = 34
    PATCH_NOTES = 35
    MONSTER_POWER_UP_COSTS = 36
    RUNE_UNEQUIP_COSTS = 37
    RUNE_UPGRADE_COSTS_AND_CHANCES = 38
    SCENARIO_REGIONS = 39
    PURCHASEABLE_ITEMS2 = 40
    EVENT_SALE = 41  # idk what is that
    MAIL_ITEMS = 42
    EVENT_PRODUCT = 43  # idk what is that
    MONSTER_FUSION_RECIPES_OLD = 44
    TOA_REWARDS = 45
    MONSTER_FUSION_RECIPES = 46
    TOA_FLOOR_MODELS_AND_EFFECTS = 47
    ELLIA_COSTUMES = 48
    GUILD_LEVELS = 49
    GUILD_BONUSES = 50
    RUNE_STAT_VALUES = 51
    GUILD_RANKS = 52
    GUILD_UNASPECTED_SUMMON_PIECES = 53  # Ifrit and Cowgirl pieces
    RUNE_BOX_INFO = 54
    MONSTER_TRANSMOGS = 55
    ELEMENTAL_RIFT_DUNGEONS = 56
    WORLD_BOSS_SCRIPT = 57
    WORLD_BOSS_ELEMENTAL_ADVANTAGES = 58
    WORLD_BOSS_FIGHT_RANKS = 59
    WORLD_BOSS_PLAYER_RANKS = 60
    SKILL_TRANSMOGS = 61
    ENCHANT_GEMS = 62
    GRINDSTONES = 63
    RUNE_CRAFT_APPLY_COSTS = 64
    RIFT_RAIDS = 65
    IRENE_EVENT_INFO = 66
    ELLIA_COSTUME_ITEMS = 67
    CHAT_BANNED_WORDS2 = 68
    CHAT_BANNED_WORDS3 = 69
    CHAT_BANNED_WORDS4 = 70
    CRAFT_MATERIALS = 71
    HOMUNCULUS_SKILL_TREES = 72
    HOMUNCULUS_CRAFT_COSTS = 73
    ELEMENTAL_DAMAGE_RANKS = 74
    WORLD_ARENA_RANKS = 75
    WORLD_ARENA_SHOP_ITEMS = 76
    CHAT_BANNED_WORDS5 = 77
    CHAT_BANNED_WORDS6 = 78
    CHAT_BANNED_WORDS7 = 79
    CHAT_BANNED_WORDS8 = 80
    ARENA_CHOICE_UI = 81
    IFRIT_TRANSMOGS = 82
    BATTLE_VERSION_INFO = 83  # idk what is that
    CHALLENGES = 84
    RTPVP_RULE_INFO = 85  # RTA battle types (normal, 4*, 20* max)
    WORLD_ARENA_SEASON_REWARDS = 86
    WORLD_ARENA_RANKS2 = 87
    WORLD_ARENA_REWARD_LIST = 88
    GUILD_SIEGE_MAP = 89
    GUILD_SIEGE_REWARD_BOXES = 90
    GUILD_SIEGE_RANKINGS = 91
    RUNE_REVALUE = 92
    LOBBY_MAP_INFO = 93
    LABYRINTH_BATTLE_TYPES = 94
    GUILD_QUESTS = 95
    LABYRINTH_BOXES = 96
    RUNE_SUB_AND_PREFIX_EFFECT_RANGES = 97  # rune_effect_value_secondary.csv in libc2ssmon.so
    ACHIEVEMENT_SCORE_REWARDS = 98
    SPECIAL_GIFTS = 99
    DIMENSIONAL_HOLE_MAP = 100
    DIMENSIONAL_HOLE_DUNGEONS = 101
    DIMENSIONAL_HOLE_MODELS = 102
    BUILDING_SKINS = 103
    TRANSMOG_EFFECTS = 104
    TUTORIAL_MAP = 105
    ARENA_LEAGUE_RANKS = 106
    ARENA_LEAGUE_REWARDS = 107
    UNIT_APPEAR_EFFECT_INFO = 108  # unitappeareffectinfo.csv
    GUILD_SIEGE_BACKGROUND_SKINS = 109
    SIEGE_SEASON_REWARDS = 110
    CHAT_BANNED_WORDS9 = 111
    CHAT_BANNED_WORDS10 = 112
    WORLD_ARENA_EMOTICONS = 113
    ARTIFACT_SUBSTAT_VALUES_OLD = 114
    ARTIFACT_ENCHANT_VALUES = 115
    ARTIFACT_SELL_VALUES = 116
    # Unknown table 117 - some x/y positions
    REPEAT_BATTLE_PLACES = 118
    WORLD_ARENA_ACHIEVEMENTS = 119
    AIR_BALOON_MODEL = 120
    # Unknown table 121 - some effects
    MOCK_BATTLE = 122
    NEW_UNITS_RESTRICTIONS = 123
    HELP_SECTION = 124
    ARTIFACT_SUBSTAT_VALUES = 125
    VALENTINE_ICONS = 126
    # Unknown table 127 - some rules
    ARENA_SKINS = 128
    # Unknown table 129 - some items; scrolls, devilmons, runes
    # Unknown table 130 - rewards
    SERVER_ARENA_BATTLE_POINTS = 131
    ALERTS = 132
    ACHIEVEMENTS2 = 133
    TRAILERS = 134
    # Unknown table 135
    RANDOM_BOX_PACK = 136
    USER_LOBBY_THEME = 137
    GUILD_LOBBY_THEME = 138
    # Unknown table 139 - Guild related rewards, drops currency (guild points + mana); maybe Monster Subjugation
    # Unknown table 140
    GUILD_BOSS_INFO = 141
    WORLD_ARENA_MONSTERS_SUPPORT = 142
    ARTIFACT_CONVERSION_COST = 143
    GUILD_BOSS_REWARDS_PHASE_2 = 144
    GUILD_BOSS_PHASES = 145
    GUILD_BOSS_REWARDS_PHASE_3 = 146
    CURRENCIES = 147
    GUILD_WAR_NPC = 148
    GUILD_WAR_RANKS = 149
    GUILD_WAR_REWARDS = 150
    CHALLENGES_2 = 151
    AC_COLLAB_GAME_MODE_BUFFS_OLD = 152
    AC_COLLAB_GAME_MODE_MONSTERS = 153
    AC_COLLAB_GAME_MODE_BUFFS = 154
    ARENA_SKINS2 = 155
    EVOLUTION_SYSTEM = 156 # needed monsters to evolve
    EVOLUTION_SYSTEM_COST = 157    
    # Unknown table 158 - Something reward-related
    # Unknown table 159 - Something quest-related
    SUMMONER_SKILLS = 160


class _LocalValueData:
    filename = 'bestiary/parse/com2us_data/localvalue.dat'
    _tables = {}
    _num_tables = None
    _table_offsets = {}
    _decrypted_data = None

    # Byte offsets for key locations in file
    VERSION_POS = 0x0
    VERSION_LEN = 0x18 * 8
    TABLE_COUNT_POS = 0x24 * 8
    TABLE_DEFS_POS = 0x34 * 8
    TABLE_START_POS = None  # Must be processed after loading table definitions

    def __getattr__(self, item):
        # Allows access to tables by name instead of index.
        value = getattr(_TableDefs, item)
        return self[value]

    def __getitem__(self, key):
        if key not in _LocalValueData._tables:
            _LocalValueData._tables[key] = _LocalValueData._get_table(key)

        return _LocalValueData._tables[key]

    def __len__(self):
        return _LocalValueData._get_num_tables()

    @property
    def version(self):
        v_bytes = self._get_raw_data()[self.VERSION_POS:self.VERSION_POS + self.VERSION_LEN].tobytes()
        return v_bytes.strip(b'\x00').decode('ascii')

    @staticmethod
    def _get_num_tables():
        if _LocalValueData._num_tables is None:
            file = _LocalValueData._get_raw_data()
            file.pos = _LocalValueData.TABLE_COUNT_POS
            _LocalValueData._num_tables = file.read(f'intle:32') - 1

        return _LocalValueData._num_tables

    @staticmethod
    def _get_table(key):
        if key not in _LocalValueData._tables:
            start, end = _LocalValueData._get_table_offsets(key)
            entire_table = _LocalValueData._get_table_string(start, end)
            _LocalValueData._tables[key] = _LocalValueData._parse_table(entire_table)

        return _LocalValueData._tables[key]

    @staticmethod
    def _get_table_string(start, end):
        f = _LocalValueData._get_raw_data()
        f.pos = _LocalValueData.TABLE_START_POS + start * 8
        return f.read(f'bytes:{end - start}').decode('utf-8').strip().splitlines()

    @staticmethod
    def _parse_table(table_string):
        table = {}
        column_headers = table_string[0].split('\t')
        for row_string in table_string[1:]:
            row = row_string.split('\t')
            row_key = try_json(row[0])
            table[row_key] = {
                column_headers[col]: try_json(value) for col, value in enumerate(row)
            }
        return table

    @staticmethod
    def _get_table_offsets(key):
        if not _LocalValueData._table_offsets:
            # Store all table offsets
            raw = _LocalValueData._get_raw_data()
            raw.pos = _LocalValueData.TABLE_DEFS_POS

            for x in range(_LocalValueData._get_num_tables()):
                table_num, start, end = raw.readlist(['intle:32'] * 3)
                _LocalValueData._table_offsets[table_num] = (start, end)

            _LocalValueData.TABLE_START_POS = raw.pos

        return _LocalValueData._table_offsets[key]

    @staticmethod
    def _get_raw_data():
        if _LocalValueData._decrypted_data is None:
            with open(_LocalValueData.filename, 'rb') as f:
                # Decryption by Lyrex;
                # With 6.2.1 update Com2uS changed `localvalue.dat` encryption format, so Joker container is not being used anymore
                # _LocalValueData._decrypted_data = JokerContainerFile(f).data
                _LocalValueData._decrypted_data = JokerContainerFile._process_mode_300(f.read())

        return ConstBitStream(_LocalValueData._decrypted_data)


class _TranslationTables:
    # Known translation table assignments
    ISLAND_NAMES = 1
    MONSTER_NAMES = 2
    SUMMON_METHODS = 10
    SKILL_NAMES = 20
    SKILL_DESCRIPTIONS = 21
    AWAKEN_STAT_BONUSES = 24
    LEADER_SKILL_DESCRIPTIONS = 25
    WORLD_MAP_DUNGEON_NAMES = 29
    CAIROS_DUNGEON_NAMES = 30
    CRAFT_MATERIAL_NAMES = 118
    CRAFT_MATERIAL_DESCRIPTIONS = 119
    DIMENSIONAL_HOLE_DUNGEON_NAMES = 169
    SUMMONER_SKILL_NAMES = 218
    SUMMONER_SKILL_DESCRIPTIONS = 219


class _Strings:
    filename = 'bestiary/parse/com2us_data/text_eng.dat'
    version = None
    _tables = []

    def __init__(self, *args, **kwargs):
        if not _Strings._tables:
            f = _Strings._get_file()

            _Strings.version = f.read('intle:32')

            try:
                while True:
                    table_len = f.read('intle:32')
                    tbl = {}

                    for _ in range(table_len):
                        str_id, str_len = f.readlist('intle:32, intle:32')
                        parsed_str = binascii.a2b_hex(f.read('hex:{}'.format(str_len * 8))[:-4])
                        tbl[str_id] = parsed_str.decode("utf-8").strip()

                    _Strings._tables.append(tbl)

            except ReadError:
                # EOF
                pass

    def __getattr__(self, item):
        # Allows access to tables by name instead of index.
        value = getattr(_TranslationTables, item)
        return self[value]

    def __getitem__(self, key):
        return _Strings._tables[key]

    def __len__(self):
        return len(_Strings._tables)

    @staticmethod
    def _get_file():
        return ConstBitStream(filename=_Strings.filename)


tables = _LocalValueData()
strings = _Strings()


def save_to_disk():
    for x in range(1, len(tables) + 1):
        tbl = tables[x]
        with open(f'bestiary/parse/com2us_data/localvalue_{x}.csv', 'w', encoding='utf-8', newline='') as f:
            if len(tbl):
                keys = tbl[list(tbl.keys())[0]].keys()
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                for row in tbl.values():
                    writer.writerow(row)

    with open('bestiary/parse/com2us_data/text_eng.csv', 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['table_num', 'id', 'text'])
        for table_idx in range(len(strings)):
            for key, text in strings[table_idx].items():
                writer.writerow([table_idx, key, text.strip()])

