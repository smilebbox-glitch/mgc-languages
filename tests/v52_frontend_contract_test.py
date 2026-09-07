import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
html=(root/'static/index.html').read_text(encoding='utf-8')
js=(root/'static/app.js').read_text(encoding='utf-8')
css=(root/'static/styles.css').read_text(encoding='utf-8')
found=json.loads((root/'data/chinese_foundations.json').read_text(encoding='utf-8'))
assert 'id="pinyinToggle"' in html
assert 'id="chineseBasicsNav"' in html
assert 'data-view="chinese-basics"' in html
for token in ('/api/chinese/foundations','/api/learning/preferences','/api/pronunciation/audio','speechSynthesis','renderChineseBasics','data-speak-text'):
    assert token in js, token
assert '.pinyin-off' in css and '.reading-off' in css
assert len(found['tones'])==5
assert found['truths'] and found['pinyin']['formula'] and found['context']['clues']
print('OK: v5.2 frontend Pinyin/foundations/audio fallback contract')
