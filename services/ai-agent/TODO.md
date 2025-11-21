Мы добавили в Actions Secrets переменную OPENAI_API_KEY, тебе необходимо написать ВСЮ ЛОГИКУ АНГЕНТА ОСНОВЫВАЯСЬ НА tr.md всего проекта и на основе всех остальных видимых тебе файлов, а также Ci/Cd скрипт, который разворачивает агентов при обновлении. 
Вот тебе пример Ci|Cd с помощью SSH
name: CI
on:
  push:
    branches: [ "main" ]
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Package build context
        run: |
          set -e
          mkdir -p ../build
          cp -TR . ../build
          tar -cvf deployAiAgent.tar ../build/

      - name: Copy file via ssh password
        uses: appleboy/scp-action@master
        with:
          host: ${{ secrets.DEPLOY_HOST }}
          username: ${{ secrets.DEPLOY_USER }}
          password: ${{ secrets.DEPLOY_PASS }}
          port: 22
          source: "deployAiAgent.tar"
          target: "/tmp/"

      - name: Build and run on remote host
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.DEPLOY_HOST }}
          username: ${{ secrets.DEPLOY_USER }}
          password: ${{ secrets.DEPLOY_PASS }}
          port: 22
          script: |
            set -e
            
            rm -rf /tmp/ai-agent|| true
            mkdir -p /tmp/ai-agent
            cd /tmp/ai-agent
            tar -xvf ../deployAiAgent.tar
            cd build

            docker build . --tag ai-agent:latest

            docker stop ai-agent || true
            docker rm ai-agent || true

            docker run -p 3001:3000 -d --name=ai-agent --restart unless-stopped  ai-agent:latest

Только необходимо, чтобы он стартовал не один, а как по TR.md несколько (не помню сколько)

Отдельно выпиши,  что ещё добавить в Actions Secrets, но OPENAI_API_KEY я тебе добавил, чтобы ты уже его заюзал и всё работало хорошо.

КРОМЕ ЭТОГО НЕ ЗАБУДЬ, что у нас не напрямую в OpenAI, у нас endpoint=https://api.proxyapi.ru/openai/v1

В общем доведи AI-agent до логично работающего MVP, который можно использовать в тестах (не до конца ясно как разворачивать их, если они прекращают работу, когда нет задания. Надо создать видимо отдельный CI|CD скрипт или ещё что-то, чтобы уже Text-service мог деплоить этих агентов сколько ему надо и когда ему надо. Прямо закончить с этой частью и логически додумать всё что надо.

НЕ ПИШИ ЛИШНИЕ .md ДОКУМЕНТЫ, МНЕ НЕКОГДА ИХ ЧИТАТЬ. ПО-МИНИМУМУ ОТЧЁТНОСТИ
