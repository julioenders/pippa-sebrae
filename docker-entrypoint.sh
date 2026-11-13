#!/bin/sh
echo "PIPPA — Plataforma de Inteligência em Políticas Públicas Aplicadas"
echo "Servindo em porta 8080"
echo "Ferramentas: $(find /usr/share/nginx/html -maxdepth 2 -name 'index.html' | wc -l) módulos"
