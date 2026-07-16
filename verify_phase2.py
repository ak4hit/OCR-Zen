"""Phase 2 verification — generates all 7 technique images, scores payload detection."""
import sys
sys.path.insert(0, '.')

from core.generator import AdversarialImageGenerator
from engines.tesseract import TesseractEngine
from difflib import SequenceMatcher

gen  = AdversarialImageGenerator()
tess = TesseractEngine()

payload  = 'id and whoami'
innocent = 'Invoice 1234 Total 500'

print('=' * 70)
print('  OCR-Zen Phase 2 Verification')
print('=' * 70)
print(f'  Payload      : {payload}')
print(f'  Innocent text: {innocent}')
print('-' * 70)
print(f'  {"Technique":<24} {"PayloadSim":>10} {"InnocentSim":>12}  {"Status":<10} Tesseract reads...')
print('-' * 70)

results = []
for tech in gen.TECHNIQUES:
    try:
        path, _ = gen.generate(payload, innocent, tech)
        preprocess = 'red_channel' if tech == 'channel_isolation' else 'none'
        raw = tess.read(path, preprocess=preprocess)
        flat = raw.replace('\n', ' ').replace('\r', '').lower()

        payload_sim  = SequenceMatcher(None, payload.lower(),  flat).ratio()
        innocent_sim = SequenceMatcher(None, innocent.lower(), flat).ratio()

        # Success = payload found anywhere in the output
        payload_in_output = payload.lower() in flat or payload_sim > 0.6
        status = 'PASS' if payload_in_output else ('PARTIAL' if payload_sim > 0.3 else 'FAIL')
        results.append((tech, payload_sim, innocent_sim, status))
        print(f'  {tech:<24} {payload_sim:>10.2f} {innocent_sim:>12.2f}  [{status:<7}] {flat[:35]}...')
    except Exception as e:
        results.append((tech, 0.0, 0.0, 'ERROR'))
        print(f'  {tech:<24} {"":>10} {"":>12}  [ERROR  ] {e}')

print('-' * 70)
ok = sum(1 for _, _, _, st in results if st == 'PASS')
partial = sum(1 for _, _, _, st in results if st == 'PARTIAL')
print(f'  PASS: {ok}/7   PARTIAL: {partial}/7   FAIL: {7-ok-partial}/7')
print(f'  Images saved to: output/images/')
print('=' * 70)
