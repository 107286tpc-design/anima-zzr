# -*- coding: utf-8 -*-
# 模板管理工具：JSON读写 + ChromaDB向量检索 + wildcard替换
# 依赖：chromadb, sentence-transformers

import os, json, re, random

# 插件目录
PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))

# HuggingFace 本地缓存路径（内嵌在插件目录，离线可用）
HF_HOME = os.path.join(PLUGIN_DIR, "hf_home")
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
os.environ.setdefault("HF_HOME", HF_HOME)
os.environ.setdefault("HF_HUB_OFFLINE", "1")

TEMPLATES_DIR = os.path.join(PLUGIN_DIR, "templates")
CHROMA_DIR = os.path.join(PLUGIN_DIR, "chroma_db")
WILDCARDS_DIR = os.path.join(PLUGIN_DIR, "wildcards")
MODELS = ["anima", "sdxl", "animaNSFW", "SDXLNSFW"]

# 通用质量/光线/画质/视角词——向量检索时跳过，不用于匹配
_QUALITY_KEYWORDS = [
    "masterpiece", "best quality", "amazing quality", "very aesthetic",
    "extremely detailed", "very detailed", "absurdres", "highres", "newest",
    "score_9", "score_8", "score_7", "safe",
    "cinematic lighting", "real background", "smooth shading",
    "glossy surfaces", "colorful depth", "soft lighting", "rim lighting",
    "masterful shading", "shallow depth of field", "foreshortening",
    "from above", "from below", "from side", "from behind",
    "dramatic angles", "dynamic angle", "low angle", "high angle",
    "vanishing point", "wide shot", "medium shot", "close-up",
    "depth of field", "bokeh", "sharp focus", "soft focus",
    "dramatic lighting", "volumetric lighting", "backlighting",
    "high contrast", "huge filesize", "very aesthetic",
    "subtle", "sketch",
    "pale_skin", "fair_skin",
]
_QUALITY_PATTERNS = [
    r'^@\w+(?:\.\d+)?\)?',            # @sw33t, @artist.weight
    r'^Clean\s+elegant\s+anime',       # Clean elegant anime linework
    r'^visible\s+construction',         # visible construction sketch lines
    r'^broken\s+line',                  # broken line edges
    r'^uneven\s+ink',                   # uneven ink detailing
    r'^visual-development',             # visual-development artwork quality
    r'^strong\s+silhouette',            # strong silhouette readability
]
_SKIP_COMPILED = [re.compile(p, re.IGNORECASE) for p in _QUALITY_PATTERNS]

# 中文→Danbooru 标签映射（离线，精确匹配模板库里的英文标签）
_ZH_TAG_MAP = {
    # 性取向 / 关系
    "女同": "yuri, girls_love, lesbian",
    "女同性恋": "yuri, girls_love, lesbian, kissing",
    "百合": "yuri, girls_love, lesbian",
    "男同": "yaoi, boys_love",
    "男同性恋": "yaoi, boys_love",
    "耽美": "yaoi, boys_love",
    "双性恋": "bisexual",
    "乱交": "gangbang, orgy",
    "群交": "gangbang, orgy",
    "杂交": "gangbang, orgy",
    # 性行为
    "性交": "sex, intercourse, having sex",
    "做爱": "sex, intercourse, having sex",
    "插入": "penetration, insertion",
    "口交": "blowjob, fellatio",
    "乳交": "paizuri, titfuck",
    "肛交": "anal, anal sex",
    "肛": "anal",
    "自慰": "masturbation, fingering",
    "手淫": "masturbation",
    "足交": "footjob",
    "手交": "handjob, hand job",
    "腿交": "thighjob",
    "深喉": "deepthroat, deep throat, irrumatio",
    "颜射": "facial, cumshot",
    "中出": "creampie, cum inside",
    "内射": "creampie, cum inside",
    "吞精": "cum swallow, swallowing",
    # 性器官
    "阴茎": "penis, dick, cock",
    "鸡巴": "penis, dick, cock",
    "阴道": "pussy, vagina",
    "小穴": "pussy, vagina",
    "阴唇": "labia, pussy lips",
    "阴蒂": "clitoris",
    "乳头": "nipples, areola",
    "乳房": "breasts, boobs",
    "胸部": "breasts, huge breasts",
    "臀部": "ass, butt",
    "肛门": "anus, anal",
    # BDSM / 束缚
    "捆绑": "bondage, tied, restrained",
    "束缚": "bound, bondage, tied up",
    "鞭打": "spanking, whipping",
    "调教": "domination, bdsm",
    "绳缚": "shibari, rope bondage",
    "窒息": "choking, breath play",
    "口球": "gag, ball gag",
    "足控": "foot fetish, feet",
    "乳控": "breast fetish, breast obsession",
    "灌肠": "enema, enema play",
    "人兽": "bestiality, animal",
    "3P": "threesome, 3some",
    "磨豆腐": "tribadism, scissoring",
    # 特殊XP
    "扶她": "futanari, dickgirl, shemale",
    "NTR": "netorare, ntr, cheating",
    "ntr": "netorare, ntr, cheating",
    "露出": "exhibitionism, public indecency",
    "催眠": "hypnosis, mind control",
    "妊娠": "pregnant, pregnancy, impregnation",
    "膨胀": "inflation, body expansion",
    "史莱姆": "slime, slime girl",
    "怪物": "monster, monster girl",
    "机械": "machine, robot, cyborg",
    "魅魔": "succubus, demon girl",
    "龙": "dragon, wyvern, dragon girl",
    "兽人": "kemonomimi, animal ears, furry",
    "肌肉": "muscular, muscle, abs",
    "腹肌": "abs, muscular, toned",
    "伪娘": "femboy, trap, crossdressing",
    "正太": "shota, young boy",
    "熟女": "milf, mature female, onee_san",
    "巨尻": "huge ass, big butt, fat ass",
    "刺青": "tattoo, tattooed",
    "穿孔": "piercing, pierced",
    "项圈": "choker, collar, neck collar",
    "口枷": "gag, ball gag, ring gag",
    "眼罩": "blindfold, eyepatch",
    "手铐": "handcuffs, cuffs, restraints",
    "绳索": "rope, rope bondage, shibari",
    "皮衣": "latex, leather, pvc",
    "胶衣": "latex, bodysuit, pvc suit",
    "紧身衣": "bodysuit, catsuit, leotard",
    "教师": "teacher, sensei, professor",
    "孕妇": "pregnant, impregnation, breeding",
    "泌乳": "lactation, milking, breast milk",
    "虫交": "insect, bug, worm",
    "植物交": "plant, tentacle plant, vine",
    "尸交": "necrophilia, undead, zombie",
    "兽交": "bestiality, animal, zoophilia",
    "失禁": "incontinence, wetting, pants wetting",
    "放尿": "urination, pissing, watersports",
    "潮吹": "squirting, female ejaculation, gushing",
    "喷水": "squirting, gushing, fountain",
    "绝顶": "orgasm, climax, multiple orgasm",
    "强制": "forced, rape, non-con",
    "洗脑": "brainwashing, mind break, corruption",
    "堕落": "corruption, degradation, moral decay",
    "痴女": "slut, whore, promiscuous",
    "荡妇": "slut, whore, nympho",
    "处女": "virgin, defloration, first time",
    "开苞": "defloration, first time, virgin blood",
    "破处": "defloration, virgin, first time",
    "纯爱": "pure love, vanilla, romantic",
    "电击": "electro, electric shock, taser",
    "蜡烛": "wax play, candle, hot wax",
    "拷问": "torture, interrogation, pain",
    "虫": "insect, bug, worm, cockroach",
    "寄生": "parasite, parasitic",
    "改造": "modification, body modification, cybernetic",
    "变身": "transformation, gender bender, tf",
    "巨大化": "giantess, macro, growth",
    "缩小": "shrink, tiny, minuscule",
    "多重人格": "multiple personalities, split personality",
    "时间停止": "time stop, frozen, timestop",
    "幽灵": "ghost, specter, spirit, apparition",
    "丧尸": "zombie, undead, walking dead",
    # 着装/裸露
    "裸体": "nude, naked, no clothes",
    "全裸": "nude, naked, fully nude",
    "半裸": "partially nude, topless",
    "一丝不挂": "nude, naked, no clothes",
    "裸露": "nude, exposed",
    "裸": "nude",
    "脱衣": "undressing, strip",
    "透视": "see-through, sheer",
    "透明": "see-through, transparent",
    "真空": "no panties, no bra",
    "内衣": "lingerie, bra, panties",
    "蕾丝": "lace, lace trim",
    "情趣": "lingerie, sexy lingerie",
    "丝袜": "stockings, pantyhose",
    "黑丝": "black stockings",
    "白丝": "white stockings",
    "过膝袜": "thighhighs, thighhigh socks",
    "吊带袜": "garter belt, suspenders",
    "比基尼": "bikini, swimsuit",
    "泳装": "swimsuit, bikini",
    # 常见搜索词
    "猫娘": "cat_ears, nekomimi, cat_girl",
    "狐娘": "fox_ears, fox_girl",
    "兔娘": "bunny_ears, bunny_girl",
    "兔女郎": "bunny_ears, bunny_girl, bunny_suit",
    "犬娘": "dog_ears, dog_girl",
    "狼娘": "wolf_ears, wolf_girl",
    "精灵": "elf, pointed ears, fantasy",
    "天使": "halo, angel_wings, angel",
    "恶魔": "demon, demon_wings, horns",
    "恶魔娘": "demon_girl, demon_wings",
    "吸血鬼": "vampire, fangs, blood",
    "女仆": "maid, maid_outfit",
    "护士": "nurse, nurse_outfit",
    "制服": "uniform, school_uniform",
    "校服": "school_uniform, sailor_uniform",
    "水手服": "sailor_uniform, sailor_suit",
    "泳衣": "swimsuit, bikini",
    "旗袍": "qipao, cheongsam",
    "和服": "kimono",
    "女巫": "witch, witch_hat",
    "公主": "princess, princess_dress",
    "婚纱": "wedding_dress, bride",
    "旗袍": "qipao, cheongsam",
    "眼镜": "glasses",
    "巨乳": "huge_breasts, big_breasts",
    "贫乳": "flat_chest, small_breasts",
    "萝莉": "loli, loli_face",
    "御姐": "onee-san, mature, adult",
    "单马尾": "ponytail, single_ponytail",
    "双马尾": "twintails, twin_tails",
    "长发": "long_hair",
    "短发": "short_hair",
    "白发": "white_hair",
    "银发": "silver_hair",
    "金发": "blonde_hair, golden_hair",
    "黑发": "black_hair",
    "红发": "red_hair",
    "蓝发": "blue_hair",
    "粉发": "pink_hair",
    "紫发": "purple_hair",
    "绿发": "green_hair",
    "棕发": "brown_hair",
    "灰发": "grey_hair",
    "双色发": "two_tone_hair, multicolored_hair",
    "异色瞳": "heterochromia, different_colored_eyes",
    "红瞳": "red_eyes",
    "蓝瞳": "blue_eyes",
    "绿瞳": "green_eyes",
    "紫瞳": "purple_eyes",
    "金瞳": "golden_eyes",
    "碧眼": "blue_eyes, green_eyes",
    "呆毛": "ahoge",
    "兽耳": "animal_ears",
    "翅膀": "wings",
    "尾巴": "tail",
    "龙娘": "dragon_girl, dragon_ears",
    "马娘": "horse_girl, horse_ears",
    "鱼尾": "tail, fish_tail",
    # NSFW 特定搜索
    "色情": "erotic, porn, explicit",
    "色色": "erotic, suggestive",
    "黄": "nsfw, explicit",
    "肉": "nsfw, explicit, flesh",
    "露点": "nipples exposed, no nipples",
    "漏点": "see-through, pasties",
    "透视装": "see-through, sheer",
    # 体位
    "传教士": "missionary, missionary_position",
    "后入": "doggy_style, from_behind, sex from behind",
    "后入式": "doggy_style, from_behind",
    "骑乘": "cowgirl, reverse_cowgirl",
    "骑乘位": "cowgirl_position, cowgirl",
    "反骑乘": "reverse_cowgirl",
    "女上位": "cowgirl, woman on top, female superior",
    "男上位": "missionary, man on top",
    "正常位": "missionary, missionary_position",
    "69": "69, 69_position, 69_pose",
    "站立": "standing_sex, standing",
    "站立位": "standing_sex, standing",
    "坐脸": "facesitting",
    "侧入": "side_sex, sideways_sex, side-by-side",
    "侧入式": "side_sex, sideways",
    "背后位": "doggy_style, from_behind",
    "对面座位": "seated_face-to-face, sitting_sex",
    "背面座位": "seated_from_behind, reverse_cowgirl",
    "屈曲位": "piledriver, leg_lock",
    "肩車": "shoulder_carry, leg_carry, suspended_sex",
    "肩扛": "shoulder_carry, suspended_sex",
    "抱起": "carrying, suspended, standing_carry",
    "抱起式": "carrying, suspended_sex",
    "趴着": "prone_bone, prone, lying_face_down",
    "仰卧": "supine, lying_on_back",
    "仰躺": "supine, lying_on_back",
    "膝上": "lap_sex, lap_sitting",
    "跨坐": "straddling, cowgirl",
    "面对面": "face-to-face, missionary",
    "背后": "from_behind, doggy_style",
    "正常体位": "missionary",
    "火车便当": "wall_sex, wall_sex_position, standing_carry",
    "火车便当式": "wall_sex, standing_carry",
    "蜘蛛": "spider_position, mating_press",
    "蜘蛛位": "spider_position",
    "压迫": "mating_press",
    "交差": "crossed_legs, leg_lock",
    "站立后入": "standing_doggy, standing_doggy_style",
    "立ちバック": "standing_doggy, standing_doggy_style",
    "まんぐり": "spread_legs, legs_behind_head",
    "腰振": "grinding, hip_movement",
    "腰振り": "grinding, hip_movement",
    "素股": "thigh_sex, intercrural, cock_warm_thighs",
    "泡芙": "creampie",
    # NSFW 类型
    "人妻": "milf, onee_san, mature",
    "公共场所": "public_sex, public_indecency, outdoor_sex",
    "公共场合": "public_sex, public_indecency, outdoor_sex",
    "户外性交": "public_sex, outdoor_sex",
    "魔物娘": "monster_girl, monster, monster_girls",
    "怪物娘": "monster_girl, monster",
    "宠物play": "petplay, pet_play, on_all_fours",
    "男性主导": "maledom, male_dominant, male_domination",
    # R18G / 猎奇
    "壁尻": "wall penetration, stuck in wall, kabehijiri",
    "秀色": "cannibalism, edible, cooking human",
    "食人": "cannibalism, eating human",
    "浣肠": "enema",
    "断头": "guillotine, beheaded, decapitation, severed head",
    "斩首": "guillotine, beheaded, decapitation",
    "拳交": "fisting",
    "奸尸": "necrophilia, corpse, dead body sex",
    "尸体": "corpse, dead body",
    "触手": "tentacle, tentacle sex",
    "机械奸": "machine sex, machine, mechanical",
    "丸吞": "vore, swallowed whole",
    "吞食": "vore, swallowing, eating",
    "穿刺": "impalement, impaled",
    "产卵": "egg laying, oviposition",
    "下蛋": "egg laying, egg",
    "人棍": "amputee, amputated limbs",
    "石化": "petrification, stone, turned to stone",
    "巨人": "giantess, giant, macro",
    "小人": "tiny, micro, miniature",
    "饮尿": "drinking urine, piss drinking, golden shower",
    # 精液/体液
    "精液": "cum, semen, seminal_fluid",
    "射精": "cumshot, ejaculation",
    "汗水": "sweat, glistening_body",
    "口水": "drool, saliva",
    "唾液": "drool, saliva, spit",
    # ══════ SFW 场景/天气/时间 ══════
    "黄昏": "sunset, dusk, golden hour",
    "黎明": "dawn, sunrise, early morning",
    "星空": "starry sky, starry night, night sky",
    "月夜": "moonlit night, moonlight, full moon",
    "晴天": "sunny, clear sky, blue sky",
    "雨天": "rainy, rain, rain drops, wet",
    "雪天": "snowy, snow, snowfall, winter",
    "樱花": "cherry blossoms, sakura, pink petals",
    "枫叶": "maple leaves, autumn leaves, red leaves",
    "花海": "flower field, flower garden, blooming",
    "森林": "forest, woods, trees, woodland",
    "海洋": "ocean, sea, waves, seaside",
    "沙漠": "desert, sand dunes, arid",
    "草原": "grassland, prairie, meadow, field",
    "雪山": "snowy mountain, snow capped mountain, alpine",
    "火山": "volcano, volcanic, lava, eruption",
    "瀑布": "waterfall, cascading water, falls",
    "湖泊": "lake, pond, still water, reflection",
    "河流": "river, stream, flowing water, creek",
    "峡谷": "canyon, gorge, valley, cliff",
    # ══════ SFW 地点 ══════
    "城市": "city, cityscape, urban, skyscraper",
    "乡村": "countryside, village, rural, farm",
    "废墟": "ruins, abandoned, destroyed, rubble",
    "古堡": "castle, fortress, medieval, gothic",
    "教堂": "church, cathedral, chapel, stained glass",
    "神社": "shrine, torii, japanese shrine, jinja",
    "寺庙": "temple, buddhist temple, pagoda",
    "学校": "school, school building, campus",
    "图书馆": "library, bookshelf, book store",
    "医院": "hospital, clinic, medical",
    "咖啡厅": "cafe, coffee shop, coffee house",
    "酒吧": "bar, pub, nightclub, tavern",
    "餐厅": "restaurant, dining room, food court",
    "商场": "shopping mall, department store, arcade",
    "公园": "park, playground, garden, bench",
    "游乐场": "amusement park, theme park, carnival",
    "水族馆": "aquarium, fish tank, marine",
    "天文台": "observatory, planetarium, telescope",
    "美术馆": "art museum, gallery, exhibition",
    "教室": "classroom, school, school room",
    "卧室": "bedroom, sleeping room",
    "浴室": "bathroom, bath, shower room",
    "海边": "beach, seaside, coast, seashore",
    "夕阳": "sunset, golden hour, dusk, twilight",
    "夜晚": "night, nighttime, night sky, dark",
    "车内": "car interior, inside car, backseat",
    "天台": "rooftop, roof, rooftop view",
    "泳池": "swimming pool, pool, poolside",
    "教堂": "church, cathedral, chapel",
    "废墟": "ruins, abandoned, desolate, wasteland",
    "阁楼": "attic, loft, garret",
    "地下室": "basement, cellar, underground",
    # ══════ SFW 情绪/氛围 ══════
    "治愈": "peaceful, healing, serene, tranquil",
    "温馨": "warm, cozy, heartwarming, gentle",
    "忧郁": "melancholic, wistful, sad, gloomy",
    "孤独": "lonely, solitude, isolated, alone",
    "紧张": "tense, suspenseful, anxious, nervous",
    "神秘": "mysterious, enigmatic, arcane, mystic",
    "神圣": "sacred, divine, holy, celestial",
    "史诗": "epic, grand, majestic, monumental",
    "热血": "passionate, intense, fierce, battle spirit",
    "浪漫": "romantic, love, tender, affectionate",
    "梦幻": "dreamy, ethereal, fantasy, surreal",
    "末世": "apocalyptic, post-apocalyptic, desolate",
    "欢快": "cheerful, joyful, happy, lively",
    "阴森": "eerie, creepy, unsettling, ominous",
    "生气": "angry, rage, furious, irritated",
    "惊讶": "surprised, shocked, astonished, startled",
    "害怕": "scared, frightened, afraid, terrified",
    "悲伤": "sad, sorrowful, grief, mournful",
    "兴奋": "excited, thrilled, ecstatic, pumped",
    "困倦": "sleepy, drowsy, tired, half-asleep",
    "害羞": "shy, embarrassed, bashful, flustered",
    "开心": "happy, cheerful, delighted, glad",
    "绝望": "despair, hopeless, anguish, devastated",
    "陶醉": "ecstatic, blissful, enchanted, mesmerized",
    # ══════ SFW 画风 ══════
    "赛璐璐": "cel shading, anime coloring, flat color",
    "厚涂": "thick paint, painterly, oil painting",
    "水彩": "watercolor, watercolor wash, watercolor painting",
    "水墨": "sumi-e, ink wash painting, chinese ink",
    "素描": "pencil sketch, graphite, charcoal drawing",
    "油画": "oil painting, canvas, impasto",
    "漫画": "manga style, manga panel, comic",
    "像素": "pixel art, 8-bit style, retro gaming",
    "复古": "retro, vintage, nostalgic, classic",
    "极简主义": "minimalist, minimalism, clean, simple",
    "浮世绘": "ukiyo-e, japanese woodblock print",
    "波普艺术": "pop art, andy warhol style, bold colors",
    "蒸汽波": "vaporwave, retro digital, 90s aesthetic",
    # ══════ SFW 灯光 ══════
    "逆光": "backlit, backlighting, silhouette",
    "侧光": "side lighting, side light, directional",
    "体积光": "volumetric light, god rays, light shafts",
    "柔光": "soft light, diffused light, gentle lighting",
    "戏剧光": "dramatic lighting, theatrical, spotlight",
    "晨雾": "morning mist, foggy, haze, misty",
    "霓虹": "neon, neon lights, neon glow",
    "烛光": "candlelight, candle, warm flicker",
    "顶光": "overhead lighting, top light, overhead light",
    "聚光灯": "spotlight, spot light, focused beam",
    "月光": "moonlight, moon light, lunar glow",
    "金色时刻": "golden hour, magic hour, warm sunset light",
    "丁达尔效应": "tyndall effect, crepuscular rays, light beams",
    "环境光": "ambient light, ambient lighting, natural light",
    # ══════ SFW 色调 ══════
    "暖色调": "warm tones, warm color palette, warm hues",
    "冷色调": "cool tones, cool color palette, cool hues",
    "莫兰迪": "morandi palette, muted colors, desaturated",
    "高对比": "high contrast, bold contrast, dramatic",
    "鲜艳": "vivid colors, saturated, vibrant",
    "黑白": "monochrome, black and white, greyscale",
    "暗调": "dark palette, low key, moody, dark tones",
    # ══════ SFW 风格/题材 ══════
    "治愈系": "healing, wholesome, fluffy, iyashikei",
    "暗黑系": "dark, grimdark, edgy, gothic",
    "哥特": "gothic, gothic lolita, dark aesthetic",
    "蒸汽朋克": "steampunk, victorian, gears, brass",
    "赛博朋克": "cyberpunk, neon city, dystopian, tech",
    "奇幻": "fantasy, magical, enchanted, fairy tale",
    "科幻": "sci-fi, futuristic, space, technology",
    # ══════ SFW 服装 ══════
    "礼服": "formal dress, evening gown, elegant dress",
    "婚纱": "wedding dress, bridal, white gown",
    # ══════ SFW 发型 ══════
    "马尾": "ponytail, high ponytail",
    "盘发": "bun, hair bun, updo, chignon",
    "麻花辫": "braid, french braid, twin braids",
    "卷发": "curly hair, wavy hair, curly",
    "直发": "straight hair, straight_hair",
    "波波头": "bob cut, bob haircut, short bob",
    "双丸子头": "double bun, odango, pigtail bun",
    "公主切": "hime cut, princess cut",
    "姬发式": "hime cut, princess cut",
    # ══════ SFW 配饰/特征 ══════
    "泪痣": "beauty mark, mole under eye, teardrop mole",
    "猫耳": "cat ears, neko, kemonomimi",
    "狗耳": "dog ears, puppy ears, inu",
    "兔耳": "rabbit ears, bunny ears, usagi",
    "精灵耳": "pointed ears, elf ears, elven ears",
    "角": "horns, demon horns, oni horns",
    "耳环": "earrings, ear piercings, hoop earrings",
    "头饰": "hair ornament, hair accessory, hairpin",
    "手套": "gloves, elbow gloves, lace gloves",
    "围巾": "scarf, neck scarf, muffler",
    "口罩": "face mask, surgical mask, mask",
    "项链": "necklace, pendant, chain",
    "发箍": "hair band, headband, alice band",
    "蝴蝶结": "ribbon, bow, hair bow",
    # ══════ SFW 表情 ══════
    "微笑": "smile, gentle smile, soft smile",
    "大笑": "laughing, wide smile, open mouth smile",
    "害羞": "shy, embarrassed, bashful, flustered",
    "哭泣": "crying, tears, weeping, sobbing",
    "闭眼": "closed eyes, eyes closed, peaceful",
    "回眸": "looking back, over shoulder, backward glance",
    "回望": "looking back, gazing back",
    "仰望": "looking up, gazing upward, skyward gaze",
    "露齿笑": "grinning, wide smile, teeth showing",
    "邪笑": "smirk, evil smile, sly smile, devious",
    "嘟嘴": "pouting, pouty face, puffed cheeks",
    "撇嘴": "frown, pouty lip, displeased",
    "哭脸": "crying face, tearful, teary eyes",
    "ahegao": "ahegao, rolled eyes, tongue out, drooling",
    "翻白眼": "rolled eyes, eyes rolled back, white eyes",
    "wink": "wink, one eye closed",
    "吐舌": "tongue out, tongue sticking out",
    "咬唇": "lip biting, biting lip",
    "俯视": "looking down, gazing downward, downward look",
    # ══════ SFW 动作 ══════
    "坐着": "sitting, seated, sitting down",
    "躺着": "lying down, reclining, lying on back",
    "跪着": "kneeling, on knees, genuflect",
    "跳跃": "jumping, leaping, mid-air, in the air",
    "奔跑": "running, jogging, sprinting, dashing",
    "飞行": "flying, floating in air, soaring, levitating",
    "漂浮": "floating, hovering, weightless, ethereal",
    "战斗": "fighting, battle, combat, action pose",
    "施法": "casting spell, magic, incantation, spellcasting",
    "弹琴": "playing piano, playing guitar, musical instrument",
    "读书": "reading book, reading, book in hand",
    "写字": "writing, pen in hand, notebook, journaling",
    "画画": "drawing, painting, sketching, easel",
    "做饭": "cooking, kitchen, chef, cooking food",
    "打扫": "cleaning, sweeping, tidying, housework",
    # ══════ SFW 人物 ══════
    "少女": "girl, young girl, teenage girl, shoujo",
    "少年": "boy, young boy, teenage boy, shounen",
    "美女": "beautiful woman, beauty, gorgeous woman, pretty girl",
    "帅哥": "handsome man, handsome boy, bishounen, pretty boy",
    "孩子": "child, kid, children, baby",
    "婴儿": "baby, infant, newborn, toddler",
    "老人": "elderly, old man, old woman, elderly person, grandparent",
    "母亲": "mother, mom, maternal",
    "父亲": "father, dad, paternal",
    "姐姐": "older sister, onee-san, big sister",
    "妹妹": "younger sister, imouto, little sister",
    "哥哥": "older brother, onii-chan, big brother",
    "弟弟": "younger brother, otouto, little brother",
    # ══════ SFW 场景 ══════
    "风景": "landscape, scenery, scenic view, panoramic view",
    "海滩": "beach, seaside, seashore, coastline",
    "山": "mountain, mountains, mountain range, hill",
    "天空": "sky, sky view, clouds, horizon",
    "云": "clouds, cloudy sky, cloud, cloudscape",
    "路": "road, path, street, pathway, trail",
    "桥": "bridge, overpass, footbridge, suspension bridge",
    "建筑": "architecture, building, structure, facade",
    "街道": "street, avenue, boulevard, alley, lane",
    "广场": "plaza, square, town square, piazza",
    "车站": "station, train station, bus station, railway station",
    "码头": "dock, pier, harbor, wharf, port",
    # ══════ SFW 风格 ══════
    "可爱": "cute, kawaii, adorable, lovely, sweet",
    "古风": "ancient Chinese style, traditional Chinese, wuxia, xianxia, Chinese fantasy",
    "电影感": "cinematic, filmic, movie still, cinematographic",
    "写实": "realistic, photorealistic, photorealism, lifelike",
    "3D": "3d, three-dimensional, 3d render, cgi",
    "卡通": "cartoon, cartoon style, toon, animated style",
    "扁平": "flat design, flat art, flat illustration, flat color",
    "插画": "illustration, art, artwork, drawn",
    # ══════ SFW 情绪 ══════
    "沉思": "contemplating, deep in thought, pondering, thoughtful",
    "专注": "focused, concentrating, absorbed, intent",
    "无聊": "bored, uninterested, listless, weary",
    "期待": "anticipating, hopeful, expectant, waiting eagerly",
    "恐惧": "fearful, terrified, horrified, frightened, scared",
    "愤怒": "furious, enraged, wrathful, livid, angry",
    "好奇": "curious, inquisitive, intrigued, wondering",
    "满足": "satisfied, content, pleased, fulfilled",
    "无奈": "helpless, resigned, sighing, giving up, frustrated",
    # ══════ SFW 服装 ══════
    "休闲": "casual, casual wear, casual clothes, loungewear",
    "正装": "formal wear, suit, formal attire, business suit",
    "运动服": "sportswear, tracksuit, athletic wear, gym clothes",
    "哥特萝莉": "gothic lolita, goth lolita, gothic fashion",
    "洛丽塔": "lolita, lolita fashion, lolita dress, lolita style",
    "汉服": "hanfu, traditional Chinese clothing, han Chinese clothing",
    "JK": "jk, japanese school uniform, seifuku, sailor uniform",
    "工装": "overalls, work clothes, boiler suit, coveralls",
    "军装": "military uniform, army uniform, soldier uniform, combat uniform",
    # ══════ SFW 配饰 ══════
    "手镯": "bracelet, bangle, wristlet, armlet",
    "戒指": "ring, wedding ring, signet ring, band",
    "王冠": "crown, tiara, coronet, regal headpiece",
    "面纱": "veil, face veil, bridal veil, sheer veil",
    "披风": "cape, cloak, mantle, shawl",
    "腰带": "belt, waist belt, sash, obi",
    "袖套": "arm sleeves, arm warmers, sleeve, gauntlets",
    "领带": "necktie, tie, bow tie, cravat",
    "领结": "bow tie, bowtie, formal bow tie",
    # ══════ SFW 动作 ══════
    "拥抱": "hugging, embrace, cuddling, holding",
    "亲吻": "kissing, kiss, smooch, making out",
    "握手": "handshake, shaking hands, clasping hands",
    "对视": "eye contact, gazing at each other, looking at each other",
    "背影": "back view, from behind, seen from behind, back silhouette",
    "侧脸": "profile, side profile, side face, profile view",
    "凝视": "staring, gazing intently, fixed gaze, staring intensely",
    "思考": "thinking, deep thought, pondering, contemplating",
    "倾听": "listening, listening intently, eavesdropping, straining to hear",
    "等待": "waiting, waiting for, patiently waiting, expectant",
    # ══════ SFW 身体部位 ══════
    "锁骨": "collarbone, clavicle, prominent collarbone",
    "后颈": "nape, back of neck, scruff of neck",
    "腋下": "armpit, underarm, bare armpit, raised arm",
    "腰": "waist, slender waist, midriff, slim waist",
    "腿": "legs, thighs, long legs, crossed legs",
    "足": "feet, foot, barefoot, sole",
    "手": "hands, hand, palms, fingers",
    "手指": "fingers, finger, slender fingers, delicate hands",
    "脚踝": "ankles, ankle, slender ankles",
    # ══════ SFW 画风 ══════
    "概念艺术": "concept art, concept design, artstation, design sheet",
    "漫画风": "manga style, comic style, cartoon style, anime style",
    "复古风": "retro style, vintage style, nostalgic style, classic style",
    "抽象": "abstract, abstract art, abstract painting, non-representational",
    "超现实": "surreal, surrealism, dreamlike, surrealist art",
    "印象派": "impressionism, impressionist, monet style, renoir",
    "波普": "pop art, pop culture, comic style pop",
    "极简": "minimalist, minimalistic, simple, clean style",
    # ══════ SFW 其他 ══════
    "战争": "war, battle, combat, warfare, military conflict",
    "末日": "apocalypse, post-apocalyptic, doomsday, end of world",
    "未来": "future, futuristic, sci-fi, cyberpunk, space age",
    "古代": "ancient, antiquity, ancient times, historical, classical",
    "武侠": "wuxia, martial arts, martial artist, chinese swordsman",
    "仙侠": "xianxia, immortal hero, cultivation, chinese fantasy",
    "修仙": "cultivation, immortal, taoist cultivation, chinese fantasy",
    "都市": "urban, city life, metropolitan, modern city",
    "校园": "campus, school life, university campus, academy",
    "职场": "workplace, office, corporate, professional environment",
    "咖啡": "coffee, coffee cup, coffee beans, latte",
    "茶": "tea, tea cup, green tea, tea ceremony",
    "音乐": "music, musical notes, sheet music, headphones",
    "书籍": "books, book, reading, literature, knowledge",
    # ══════ NSFW 补充 ══════
    "春药": "aphrodisiac, sex drugs, lust potion",
    "媚药": "aphrodisiac, love potion, sex drug",
    "睡奸": "sleeping sex, somnophilia, molestation while asleep",
    "逆推": "reverse rape, female on male, forceful woman, aggressive female",
    "监禁": "imprisonment, confinement, captivity, trapped",
    "拘束": "restraint, restrained, bound, tied up",
    "触手调教": "tentacle bondage, tentacle rape, tentacle bdsm",
    "尿道": "urethra, urethral insertion, sounding",
}

# 编译中文关键词列表（按长度降序，优先匹配长词）
_ZH_KEYS = sorted(_ZH_TAG_MAP.keys(), key=len, reverse=True)
_ZH_PATTERN = re.compile("|".join(re.escape(k) for k in _ZH_KEYS))


def _expand_chinese_query(query):
    """将查询词扩展为中文+英文Danbooru标签，提升向量检索命中率"""
    # 先检查是否直接匹配映射表中的非中文关键词（如 3P、69 等）
    query_lower = query.strip().lower()
    for key in _ZH_KEYS:
        if key.lower() == query_lower and not re.search(r'[\u4e00-\u9fff]', key):
            return query + ", " + _ZH_TAG_MAP[key]
    if not re.search(r'[\u4e00-\u9fff]', query):
        return query  # 无中文字符，不扩展
    # 查找匹配的中文关键词，追加对应的英文标签
    seen = set()
    expansions = []
    for m in _ZH_PATTERN.finditer(query):
        key = m.group()
        if key not in seen:
            seen.add(key)
            expansions.append(_ZH_TAG_MAP[key])
    if not expansions:
        return query
    expanded = query + ", " + ", ".join(expansions)
    # 缩短到 300 字符以内，避免过长
    if len(expanded) > 300:
        expanded = expanded[:300].rsplit(",", 1)[0]
    return expanded

_embedder = None
_chroma_client = None


def _get_embedder():
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer
        local_path = os.path.join(HF_HOME, "hub", "models--BAAI--bge-small-zh-v1.5",
                                   "snapshots", "7999e1d3359715c523056ef9478215996d62a620")
        if os.path.exists(local_path):
            _embedder = SentenceTransformer(local_path)
        else:
            # 本地没有，从 HF 镜像下载（__init__.py 已设置 HF_ENDPOINT）
            _embedder = SentenceTransformer("BAAI/bge-small-zh-v1.5")
    return _embedder


def _get_chroma():
    global _chroma_client
    if _chroma_client is None:
        import chromadb
        _chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
    return _chroma_client


def _get_collection(model):
    client = _get_chroma()
    try:
        collection = client.get_collection(f"prompts_{model}")
        templates = load_templates(model)
        good_count = sum(1 for t in templates if _is_good_prompt(t.get("prompt","")))
        if collection.count() != good_count:
            sync_to_chroma(model)
            return client.get_collection(f"prompts_{model}")
        return collection
    except Exception:
        sync_to_chroma(model)
        return client.get_collection(f"prompts_{model}")


def _json_path(model):
    return os.path.join(TEMPLATES_DIR, f"{model}.json")


def load_templates(model):
    path = _json_path(model)
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_templates(model, templates):
    os.makedirs(TEMPLATES_DIR, exist_ok=True)
    with open(_json_path(model), "w", encoding="utf-8") as f:
        json.dump(templates, f, ensure_ascii=False, indent=2)


def add_template(model, prompt, category="通用", note=""):
    templates = load_templates(model)
    new_id = max((t["id"] for t in templates), default=0) + 1
    entry = {"id": new_id, "prompt": prompt, "category": category, "note": note}
    templates.append(entry)
    save_templates(model, templates)
    return entry


def delete_template(model, template_id):
    templates = [t for t in load_templates(model) if t["id"] != template_id]
    save_templates(model, templates)


def _is_quality_tag(tag):
    """判断一个tag是否为通用质量/光线/画质词"""
    tag_clean = tag.strip().strip("()").strip()
    if not tag_clean:
        return True
    tag_lower = tag_clean.lower()
    # 检查关键词列表
    for kw in _QUALITY_KEYWORDS:
        if kw in tag_lower:
            return True
    # 检查正则模式
    for p in _SKIP_COMPILED:
        if p.match(tag_clean):
            return True
    return False


def _extract_search_key(prompt, max_chars=250):
    """从prompt中提取核心标签部分用于向量检索，跳过通用质量词前缀"""
    if not prompt:
        return ""
    # 按逗号分割标签
    tags = re.split(r',\s*', prompt)
    # 找到第一个非质量标签
    start_idx = 0
    for i, tag in enumerate(tags):
        if not _is_quality_tag(tag):
            start_idx = i
            break
    # 从核心标签开始取前 max_chars 字符
    core = ", ".join(tags[start_idx:]).strip()
    if len(core) > max_chars:
        core = core[:max_chars].rsplit(",", 1)[0]
    return core


def sync_to_chroma(model):
    templates = load_templates(model)
    if not templates:
        return
    # 重新编号所有 id（去重），补全缺失字段，回写 JSON
    changed = False
    for i, t in enumerate(templates, 1):
        old_id = t.get("id")
        if old_id != i or "category" not in t or "note" not in t:
            changed = True
        t["id"] = i
        t.setdefault("category", "通用")
        t.setdefault("note", "")
    if changed:
        save_templates(model, templates)
        print(f"[ZZR] {model}: 重新编号 {len(templates)} 条模板")
    client = _get_chroma()
    try:
        client.delete_collection(f"prompts_{model}")
    except Exception:
        pass
    collection = client.create_collection(f"prompts_{model}", metadata={"hnsw:space": "cosine"})
    # 过滤掉单标签/模板槽位等畸形数据，只嵌入完整提示词
    good_templates = [t for t in templates if _is_good_prompt(t["prompt"])]
    skipped = len(templates) - len(good_templates)
    # 提取每条的搜索键（去质量词）用于嵌入
    search_keys = [_extract_search_key(t["prompt"]) for t in good_templates]
    full_prompts = [t["prompt"] for t in good_templates]
    embeddings = _get_embedder().encode(search_keys).tolist()
    ids = [f"{model}_{t['id']}" for t in good_templates]
    # metadata 存完整信息和原文
    metas = [{"full_prompt": t["prompt"], "category": t.get("category", ""), "note": t.get("note", "")} for t in good_templates]
    # ChromaDB 有 batch size 限制，分批写入
    batch_size = 2000
    for start in range(0, len(good_templates), batch_size):
        end = min(start + batch_size, len(good_templates))
        collection.add(
            ids=ids[start:end],
            embeddings=embeddings[start:end],
            documents=search_keys[start:end],
            metadatas=metas[start:end],
        )
    print(f"[ZZR] {model}: 重建向量库完成，{len(good_templates)} 条（跳过 {skipped} 条畸形数据）")


def _add_to_chroma(model, entry):
    if not _is_good_prompt(entry.get("prompt", "")):
        print(f"[ZZR] 跳过畸形数据: id={entry.get('id')} '{entry.get('prompt','')[:60]}...'")
        return
    client = _get_chroma()
    try:
        collection = client.get_collection(f"prompts_{model}")
    except Exception:
        sync_to_chroma(model)
        collection = client.get_collection(f"prompts_{model}")
    search_key = _extract_search_key(entry["prompt"])
    embedding = _get_embedder().encode([search_key]).tolist()
    collection.add(
        ids=[f"{model}_{entry['id']}"], embeddings=embedding,
        documents=[search_key],
        metadatas=[{"full_prompt": entry["prompt"], "category": entry.get("category", ""), "note": entry.get("note", "")}],
    )


def _is_good_prompt(prompt):
    """判断是否为可用提示词（过滤模板槽位碎片和单标签触发词）"""
    if not prompt:
        return False
    # 过滤模板槽位标记
    if re.search(r'char[12][：:]|此处加入', prompt):
        return False
    # 过滤单标签触发词（无逗号且长度短）
    if ',' not in prompt and len(prompt.strip()) < 40:
        return False
    # 过滤标签数过少的条目（只有1-2个标签）
    tag_count = len([t for t in prompt.split(',') if t.strip()])
    if tag_count < 3:
        return False
    return True


def search_templates(model, query, top_n=3):
    collection = _get_collection(model)
    if collection.count() == 0:
        return []
    # 提取中文映射的英文标签
    boost_tags = _get_boost_tags(query)
    search_query = _expand_chinese_query(query)

    seen = set()
    results = []

    # 策略1：有中文映射 → 先关键词搜索（保证命中）
    if boost_tags:
        keyword_results = _keyword_search(collection, boost_tags, top_n * 3)
        for r in keyword_results:
            if r["prompt"] not in seen:
                seen.add(r["prompt"])
                results.append(r)

    # 策略2：向量搜索补充（凑够数量）
    if len(results) < top_n:
        search_key = _extract_search_key(search_query)
        if not search_key.strip():
            search_key = search_query
        query_emb = _get_embedder().encode([search_key]).tolist()
        fetch_n = min(max(top_n * 4, 50), collection.count())
        res = collection.query(query_embeddings=query_emb, n_results=fetch_n)
        docs, metas = res.get("documents", [[]])[0], res.get("metadatas", [[]])[0]
        for d, m in zip(docs, metas):
            full = m.get("full_prompt", d)
            if full in seen:
                continue
            seen.add(full)
            if not _is_good_prompt(full):
                continue
            results.append({
                "prompt": full,
                "category": m.get("category", ""),
                "note": m.get("note", ""),
            })

    # 随机化：从候选池中随机抽
    import random
    pool_size = min(top_n * 3, len(results))
    pool = results[:pool_size]
    if len(pool) > top_n:
        results = random.sample(pool, top_n)
    else:
        results = pool
    return results


def _keyword_search(collection, boost_tags, limit):
    """直接用关键词搜索模板库（兜底方案）"""
    all_data = collection.get(include=["documents", "metadatas"])
    if not all_data.get("documents"):
        return []
    results = []
    seen = set()
    for doc, meta in zip(all_data["documents"], all_data["metadatas"] or []):
        full = meta.get("full_prompt", doc)
        if full in seen:
            continue
        seen.add(full)
        if not _is_good_prompt(full):
            continue
        # 检查是否包含boost标签
        p_lower = full.lower()
        if any(t in p_lower for t in boost_tags):
            results.append({
                "prompt": full,
                "category": meta.get("category", ""),
                "note": meta.get("note", ""),
            })
            if len(results) >= limit:
                break
    return results


def _get_boost_tags(query):
    """从映射表提取查询对应的英文标签列表（用于搜索后二次排序）"""
    tags = []
    for m in _ZH_PATTERN.finditer(query):
        key = m.group()
        if key in _ZH_TAG_MAP:
            # 拆分 "urination, pissing, watersports" → ["urination", "pissing", "watersports"]
            for t in _ZH_TAG_MAP[key].split(","):
                t = t.strip().lower()
                if t and t not in tags:
                    tags.append(t)
    return tags


def _boost_score(prompt, boost_tags):
    """计算模板与目标标签的匹配度（0~1），用于二次排序"""
    p_lower = prompt.lower()
    hits = sum(1 for t in boost_tags if t in p_lower)
    return hits / len(boost_tags) if boost_tags else 0


def random_sample_templates(model_name, count, wildcards_dir=None, do_replace=True):
    collection = _get_collection(model_name)
    if collection.count() == 0:
        return []
    all_data = collection.get(include=["documents", "metadatas"])
    docs, metas = all_data.get("documents", []), all_data.get("metadatas", [])
    if not docs:
        return []
    n = min(count, len(docs))
    results = []
    for i in random.sample(range(len(docs)), n):
        prompt = docs[i]
        meta = metas[i] if metas else {}
        # 抽卡模式取完整prompt
        full_prompt = meta.get("full_prompt", prompt)
        if do_replace:
            full_prompt = replace_wildcards(full_prompt, wildcards_dir)
        results.append({"prompt": full_prompt, "category": meta.get("category", ""), "note": meta.get("note", "")})
    return results


def init_all_chroma():
    for model in MODELS:
        try:
            sync_to_chroma(model)
        except Exception as e:
            print(f"[ZZR] 同步 {model} 到 ChromaDB 失败: {e}")


def replace_wildcards(prompt_text, wildcards_dir=None):
    if wildcards_dir is None:
        wildcards_dir = WILDCARDS_DIR

    def replacer(match):
        key = match.group(1)
        filepath = os.path.join(wildcards_dir, f"{key}.json")
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    options = json.load(f)
                if options:
                    return random.choice(options)
            except Exception:
                pass
        return match.group(0)

    # 1. 先处理 {{option1, option2, ...}} 内联选择语法
    def inline_replacer(match):
        options = [o.strip() for o in match.group(1).split(",") if o.strip()]
        return random.choice(options) if options else match.group(0)

    result = re.sub(r'\{\{([^}]+)\}\}', inline_replacer, prompt_text)
    # 2. 再处理 {wildcard_name} 文件引用语法
    result = re.sub(r'\{(\w+)\}', replacer, result)
    return result
