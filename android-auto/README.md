# Moto スポット (Android Auto)

Android Auto 上で、近くの **ガソリンスタンド / バイク駐車場 / 休憩スポット** を地図つきリストで探し、
既定のナビアプリへ案内を引き渡す POI アプリ(Car App Library 使用)。

## 画面

1. **カテゴリ選択**(`ListTemplate`)— 3 種類から選ぶ。
2. **スポット一覧**(`PlaceListMapTemplate`)— 近い順に最大 6 件、20 km 以内。地図に番号マーカー、
   起点に青いマーカー。位置情報の権限がないときは東京駅付近を起点にし、
   「現在地を使う」ボタン(停車中のみ)で権限を求める。
3. **詳細**(`PaneTemplate`)— 距離・住所・メモと「ナビ開始」
   (`CarContext.ACTION_NAVIGATE` + `geo:` URI)。

## 構成

```
android-auto/
├── core/   Android 非依存の Kotlin(距離計算・検索・表示用距離・サンプルデータ)+ 単体テスト
└── app/    Android Auto アプリ本体(CarAppService / Session / Screen)
```

`core` は `includeBuild` された独立ビルドで、Android SDK なしでテストできる:

```
gradle -p android-auto/core test
```

## ビルドと実行

前提: Android Studio(または Android SDK 35 + JDK 17 以上)。

1. Android Studio で `android-auto/` を開く(Gradle Wrapper が必要なら `gradle wrapper` で生成)。
2. `app` をスマホにインストール。
3. PC で Desktop Head Unit (DHU) を使うか、車載器に接続して確認する。
   - スマホの Android Auto 設定で「開発者モード」を有効にし、「提供元不明のアプリ」を許可する。
   - デバッグビルドはすべてのホストからの接続を許可する(`MotoCarAppService.createHostValidator`)。

## 本番化の前にやること

- **データ**: `SampleSpots` は東京駅周辺の**ダミーデータ**(実在の施設ではない)。
  `SpotRepository` を実データ源(自前 API、オープンデータ等)で実装して差し替える。
- **ホスト許可リスト**: `app/src/main/res/values/hosts_allowlist.xml` が空のため、
  リリースビルドはどのホストからも接続を拒否する。Android Auto などのホストを登録する。
- **アイコン**: 現在はシステムのアイコンを仮に使用している。
- **ストア審査**: POI カテゴリの品質ガイドライン(Car app quality guidelines)を確認する。

## 検証状況

- `core` の単体テストは `gradle -p android-auto/core test` で実行する(作成時点の実行結果はコミット履歴を参照)。
- `app` は、作成した環境から Google Maven(`dl.google.com`)へ接続できなかったため、**ビルド未確認**。
  使用している Car App Library の API は androidx のソースで存在とシグネチャを確認したが、
  初回は Android Studio でビルドし、DHU で動作確認すること。
