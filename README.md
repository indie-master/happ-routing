# Happ Routing

Автоматическая сборка собственных `geosite.dat` и `geoip.dat` для Happ с
правилами RoscomVPN, актуальными community-списками и локальными дополнениями.

## Что маршрутизируется

- Google — напрямую через `geosite:google-direct`; рекламная категория
  `geosite:google-ads` остаётся на прокси и имеет приоритет над DIRECT.
- YouTube и Google Play — через прокси; они проверяются раньше DIRECT благодаря
  `RouteOrder: block-proxy-direct`.
- WeChat / Weixin — напрямую через узкую категорию `geosite:wechat` и известные
  адреса `geoip:wechat`.
- Вся широкая сеть Google и весь Tencent Cloud намеренно не добавляются в
  `DirectIp`, чтобы не перехватить посторонний трафик.

## Источники

- `v2fly/domain-list-community` — свежая полная доменная база и Google.
- `hydraponique/roscomvpn-geosite` — категории RoscomVPN.
- `hydraponique/roscomvpn-geoip` — готовые отфильтрованные списки
  `direct`, `private`, `whitelist`.
- `Loyalsoldier/geoip` — сборщик итогового `geoip.dat`.
- `custom/` — локальные категории Google Direct и WeChat.

Точные commit SHA всех источников записываются в `release/manifest.json`.

## Автообновление

Workflow `Build and publish Happ geodata` запускается ежедневно в `03:37 UTC`,
а также вручную и после изменения исходников. Он:

1. получает текущие upstream-списки;
2. собирает обе базы;
3. проверяет наличие всех категорий через `v2dat`;
4. создаёт SHA256 и манифест;
5. формирует production и canary deeplink;
6. публикует неизменяемый тег и GitHub Release;
7. проверяет доступность файлов через jsDelivr.

Production deeplink:

```text
https://raw.githubusercontent.com/indie-master/happ-routing/main/HAPP/DEFAULT.DEEPLINK
```

Canary deeplink с отдельным именем профиля:

```text
https://raw.githubusercontent.com/indie-master/happ-routing/main/HAPP/CANARY.DEEPLINK
```

Оба deeplink используют `happ://routing/add/`, поэтому обновление подписки не
переключает активный профиль принудительно.

## DNS

В профиле настроены:

- Remote DoH: `https://dns.google/dns-query`, bootstrap `8.8.8.8`;
- Domestic DoH: `https://common.dot.dns.yandex.net/dns-query`, bootstrap
  `77.88.8.8`;
- статические записи bootstrap в `DnsHosts`;
- `DomainStrategy: IPIfNonMatch`, `FakeDNS: false`.

## Безопасный откат

Запустите workflow `Roll back Happ profile`, укажите предыдущий release tag.
Workflow оставит старые проверенные базы, но выставит новый `LastUpdated`, чтобы
Happ не проигнорировал откат.

## Локальная проверка

Требуются Go, Python 3 и `v2dat`:

```bash
go install github.com/urlesistiana/v2dat@47b8ee51fb528e11e1a83453b7e767a18d20d1f7
./scripts/build_geodata.sh
python3 scripts/generate_release.py \
  --repo indie-master/happ-routing \
  --tag local-test \
  --timestamp "$(date -u +%s)"
./scripts/validate_release.sh
```

## Лицензии источников

Код этого репозитория распространяется по MIT. Данные и сгенерированные базы
могут включать материалы upstream-проектов; их собственные лицензии и условия
атрибуции продолжают действовать.
