# Dialect Comparison Content Note — v5.5

## Purpose
The comparison block is an **orientation aid for Russian-speaking beginners**. Its goal is to explain why a learner may recognize a written Chinese word but fail to recognize the same meaning in regional speech.

It is not a dialect course, not a competence score and not a substitute for a Language Expert review.

## Core content rule
The platform teaches **普通话 / Putonghua first**. The Ministry of Education overview describes Putonghua as the standard variety of modern Chinese and lists ten major dialect groups. The UI deliberately says “10 major groups”, not “China has exactly 10 dialects”.

Official overview:
https://www.moe.gov.cn/jyb_sjzl/wenzi/202108/t20210827_554992.html

## Comparison examples used
### 你好 — hello
- Putonghua: `nǐ hǎo` (Hanyu Pinyin)
- Cantonese: `nei5 hou2` (Jyutping)
- Shanghai Wu: `侬好`, `non6 hau5` in the selected Wu romanization reference
- Meixian Hakka example: `ngi2 hau3`
- Southern Min/Hokkien orientation: `汝好`, `lí hó` in POJ-style notation

### 吃饭 — eat / have a meal
- Putonghua: `chīfàn`
- Chengdu/Sichuan example: `ci2 fan4` (Sichuanese Pinyin)
- Cantonese examples: `sik6 faan6` / colloquial `jaak3 faan6`
- Shanghai Wu example: `chiq7 ve6`
- Nanchang Gan orientation: `qiah6 fan5`

### 我不知道 — I do not know
- Putonghua: `wǒ bù zhīdào`
- Cantonese conversational example: `我唔知`, `ngo5 m4 zi1`
- Shanghai conversational example: `我勿晓得`; the UI intentionally does not invent Pinyin for it.

## Source references for the example layer
- PRC Ministry of Education, 中国语言文字概况（2021年版）:
  https://www.moe.gov.cn/jyb_sjzl/wenzi/202108/t20210827_554992.html
- Wiktionary, 你好 (multi-variety pronunciation overview):
  https://en.wiktionary.org/wiki/%E4%BD%A0%E5%A5%BD
- Wiktionary, 儂好 / 侬好 (Shanghai Wu):
  https://zh.wiktionary.org/zh/%E5%84%82%E5%A5%BD
- Wiktionary, 吃飯 / 吃饭 (Putonghua, Chengdu, Cantonese, Shanghai Wu, Gan examples):
  https://zh.wiktionary.org/zh/%E5%90%83%E9%A3%AF
- Wiktionary, 汝好 (Min/Hokkien examples):
  https://en.wiktionary.org/wiki/%E6%B1%9D%E5%A5%BD
- Jyut Dictionary, 我唔知:
  https://jyutdictionary.com/dictionary/entry/%E6%88%91%E5%94%94%E7%9F%A5

## Pronunciation safety boundary
The local TTS engine is configured for standard Mandarin and English. It must **not** be used to pretend to speak Cantonese, Shanghai Wu, Hokkien, Hakka, Gan or another regional variety.

Therefore:
- Putonghua examples can have the normal ▶ playback button.
- Regional comparison cards show written form + named romanization system + a deliberately approximate Russian orientation.
- No regional audio is generated unless a future release adds separately validated regional voice assets.

## Romanization warning
Pinyin, Jyutping, POJ and Wu/Hakka regional systems are different notation systems. Tone numbers such as `nei5 hou2` are **tone labels**, not digits spoken aloud. Some systems and local pronunciations vary by city/community, so this content should remain an orientation layer rather than an exam syllabus.
