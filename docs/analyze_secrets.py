#!/usr/bin/env python3
"""Busca por referências a 'secret' no server.py do OpenTracy."""
import re

path = '/home/hiatus/Projetos/ligadotattoo/OpenTracy/runtime/server.py'
with open(path) as f:
    data = f.read()

lines = data.split('\n')
print(f"Total de linhas: {len(lines)}")
print(f"Total de caracteres: {len(data)}")
print()

# Procura linhas com 'secret'
count = 0
for i, line in enumerate(lines, 1):
    if 'secret' in line.lower():
        print(f"L{i}: {line}")
        count += 1
        if count >= 60:
            print("... (truncado após 60 matches)")
            break

if count == 0:
    print("NENHUMA linha com 'secret' encontrada!")
    
    # Vamos verificar se o arquivo foi lido corretamente
    print("\n--- Primeiras 5 linhas ---")
    for i, line in enumerate(lines[:5], 1):
        print(f"L{i}: {line}")
    
    print("\n--- Procurando por 'Secret' (case sensitive) ---")
    for i, line in enumerate(lines, 1):
        if 'Secret' in line:
            print(f"L{i}: {line}")
            count += 1
            if count >= 20:
                break
