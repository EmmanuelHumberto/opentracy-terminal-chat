#!/usr/bin/env python3
"""Script para gerar o chat.py completo."""
import sys
sys.path.insert(0, "/home/hiatus/Projetos/ligadotattoo/opentracy-terminal-chat")

# Conteudo da primeira parte (ja existente no chat.py atual)
# Vamos ler o que ja existe e completar

with open("/home/hiatus/Projetos/ligadotattoo/opentracy-terminal-chat/app/chat.py", "r") as f:
    existing = f.read()

# Verificar onde termina
print(f"Tamanho atual: {len(existing)} chars")
print("Ultimas linhas:")
for line in existing.split("\n")[-5:]:
    print(f"  {line}")
