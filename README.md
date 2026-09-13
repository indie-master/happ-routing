# swiftless-routing for Happ

Автоматическая сборка собственных `geosite.dat` и `geoip.dat` для Happ. В
итоговой конфигурации используются категории `swiftless-*`; RoscomVPN остаётся
только одним из источников данных и не определяет имя профиля.

## Маршрутизация

- Российские домены идут напрямую через `geosite:swiftless-ru`. Категория
  объединяет полный `v2fly/category-ru` (включая `.ru`, `.рф`, `.su` и другие
  российские TLD), дополнительные записи RoscomVPN и его обязательный
  whitelist.
- Российские адреса идут напрямую через `geoip:swiftless-ru` и
  `geoip:swiftless-ru-whitelist`. IP-правила помогают и для соединений без
  доменного имени.
- Сайты из `category-geoblock-ru`, которым нужен зарубежный IP, проверяются в
  PROXY раньше широкой российской DIRECT-категории.
- WeChat / Weixin идёт напрямую по `geosite:swiftless-wechat` и
  `geoip:swiftless-wechat`. При каждой сборке домены и известные IPv4/IPv6
  диапазоны обновляются из сфокусированного списка blackmatrix7 и объединяются
  с локальными дополнениями. Весь AS132203 не добавляется: он включает
  посторонние ресурсы Tencent Cloud.
- Google идёт напрямую через `geosite:swiftless-google-direct`. Google Ads,
  Google Play, YouTube и геоблокированные Google-сервисы остаются в PROXY и
  имеют приоритет благодаря `RouteOrder: block-proxy-direct`.
- Private, Apple, Microsoft и ранее настроенные игровые/медиа-категории
  сохраняют прежнее поведение.

Если прокси-сервер недоступен, совпавшие DIRECT-правила продолжают выводить
трафик через IP самого устройства, пока локальный туннель и Xray в Happ
работают. PROXY-сайты при недоступном сервере работать не смогут. Ни один
профиль маршрутизации не может сохранить соединения, если сам Happ завершил
туннель или в ОС включён отдельный kill switch.

## DNS

- Tunnel/Remote DNS: Google DoH `https://dns.google/dns-query`, bootstrap
  `8.8.8.8`; запросы идут через прокси.
- Domestic DNS: Yandex DNS по UDP (`DoU`) `77.88.8.8`; запросы DIRECT-ресурсов
  не зависят от прокси-сервера.
- `DnsHosts` содержит bootstrap для Google DoH и необходимые статические записи
  ФНС.
- `DomainStrategy: IPIfNonMatch`, `FakeDNS: false`, `UseChunkFiles: true`.

Yandex-хост `common.dot.dns.yandex.net` намеренно не используется как DoH:
`/dns-query` у него отвечает `404`.

## Профили и миграция имени

Production-профиль называется `swiftless-routing`:

```text
https://raw.githubusercontent.com/indie-master/happ-routing/main/HAPP/DEFAULT.DEEPLINK
```

`DEFAULT.DEEPLINK` использует `happ://routing/onadd/`. Это нужно для перехода с
имени `RoscomVPN`: Happ атомарно обновляет профиль только при совпадающем имени,
а `onadd` активирует новый профиль лишь после успешной загрузки геобаз.

Canary с отдельным именем:

```text
https://raw.githubusercontent.com/indie-master/happ-routing/main/HAPP/CANARY.DEEPLINK
```

На время миграции сохраняется `HAPP/LEGACY.DEEPLINK` со старым именем. Он
использует те же новые базы и правила, но позволяет быстро вернуть прежнюю
идентичность профиля без отката данных.

## Источники и обновление

- `v2fly/domain-list-community` — полная community-база и исходный
  `category-ru`;
- `hydraponique/roscomvpn-geosite` — whitelist, исключения и дополнительные
  категории;
- `hydraponique/roscomvpn-geoip` — отфильтрованные RU/BY и whitelist CIDR;
- `blackmatrix7/ios_rule_script` — актуальные сфокусированные правила WeChat;
- `Loyalsoldier/geoip` — сборщик итогового `geoip.dat`;
- `custom/` — локальные дополнения Swiftless.

Workflow `Build and publish Happ geodata` запускается ежедневно в `03:37 UTC`,
вручную, при изменениях в `main`, а также полностью проверяет pull request без
публикации. Он фиксирует commit SHA всех источников в
`release/manifest.json`, проверяет категории через `v2dat`, публикует
неизменяемый тег и GitHub Release и затем проверяет доступность файлов через
jsDelivr.

## Безопасный откат

Workflow `Roll back Happ profile` принимает предыдущий release tag. Он оставит
проверенные старые базы, но поднимет `LastUpdated`, чтобы Happ не проигнорировал
откат. Полный legacy-профиль также публикуется в каждом release.

## Локальная проверка

Требуются Go, Python 3 и `v2dat`. Исходники upstream должны находиться в
`.upstream/` так же, как в GitHub Actions.

```bash
go install github.com/urlesistiana/v2dat@47b8ee51fb528e11e1a83453b7e767a18d20d1f7
./scripts/build_geodata.sh
python3 scripts/generate_release.py \
  --repo indie-master/happ-routing \
  --tag local-test \
  --timestamp "$(date -u +%s)"
./scripts/validate_release.sh
```

Быстрые Python-тесты:

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile scripts/*.py
```

## Лицензии

Код репозитория распространяется по MIT. Данные и сгенерированные базы могут
включать материалы upstream-проектов; их собственные лицензии и условия
атрибуции продолжают действовать.
