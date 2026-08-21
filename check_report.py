import sys
sys.path.insert(0, '.')
with open('data/reports/semanal_2026-08-20.md', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the sovereign risk section
idx = content.find('Índice de Riesgo Soberano')
if idx == -1:
    idx = content.find('Riesgo Soberano')
if idx != -1:
    print(content[idx:idx+1000])