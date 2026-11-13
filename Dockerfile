FROM nginx:1.27-alpine

LABEL maintainer="UPP — Unidade de Políticas Públicas <upp@sebrae.com.br>"
LABEL description="PIPPA — Plataforma de Inteligência em Políticas Públicas Aplicadas"

RUN rm -rf /usr/share/nginx/html/*

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY docker-entrypoint.sh /docker-entrypoint.d/40-pippa.sh
RUN chmod +x /docker-entrypoint.d/40-pippa.sh

COPY catalogo-fontes/    /usr/share/nginx/html/catalogo-fontes/
COPY docs/               /usr/share/nginx/html/docs/
COPY pippa-atuacao-upp/  /usr/share/nginx/html/pippa-atuacao-upp/
COPY pippa-cadunico/    /usr/share/nginx/html/pippa-cadunico/
COPY pippa-compras-dashboard/ /usr/share/nginx/html/pippa-compras-dashboard/
COPY pippa-consultas-publicas/ /usr/share/nginx/html/pippa-consultas-publicas/
COPY pippa-credito-fomento/   /usr/share/nginx/html/pippa-credito-fomento/
COPY pippa-emendas/      /usr/share/nginx/html/pippa-emendas/
COPY pippa-impacto/      /usr/share/nginx/html/pippa-impacto/
COPY pippa-impostometro/ /usr/share/nginx/html/pippa-impostometro/
COPY pippa-legislativo/  /usr/share/nginx/html/pippa-legislativo/
COPY pippa-legislativo-dashboard/ /usr/share/nginx/html/pippa-legislativo-dashboard/
COPY pippa-mindmap-nal/  /usr/share/nginx/html/pippa-mindmap-nal/
COPY pippa-orcamento/    /usr/share/nginx/html/pippa-orcamento/
COPY pippa-pauta-legislativa/ /usr/share/nginx/html/pippa-pauta-legislativa/
COPY pippa-pesquisas-eleitorais/ /usr/share/nginx/html/pippa-pesquisas-eleitorais/
COPY pippa-portal/       /usr/share/nginx/html/pippa-portal/
COPY pippa-projeto-2027/ /usr/share/nginx/html/pippa-projeto-2027/
COPY pippa-quem-somos/   /usr/share/nginx/html/pippa-quem-somos/
COPY pippa-reforma-dashboard/ /usr/share/nginx/html/pippa-reforma-dashboard/
COPY pippa-regulatorio/  /usr/share/nginx/html/pippa-regulatorio/
COPY pippa-stakeholders/ /usr/share/nginx/html/pippa-stakeholders/
COPY pippa-transformalab/ /usr/share/nginx/html/pippa-transformalab/

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget -qO- http://localhost:8080/healthz || exit 1
