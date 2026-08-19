# Web UI

## 調査

- 実際に利用されるroute、認証、データ取得、既存状態管理を確認する。
- 既存のCSS方式、コンポーネント層、セマンティックトークン、ブレークポイントを優先する。
- ユーザーが維持を求めた既存画面や領域を勝手に再設計しない。
- サーバー側も変更した場合、古いプロセスで確認しない。

## 実装

- Button、Input、Select、Dialog、Card、アイコンなどの正規コンポーネントを再利用する。
- 同じ役割のコントロールは高さ、幅ポリシー、文字、アイコン、focus、loading、disabled表現を統一する。
- 主要アクションは各領域につき原則1つにする。
- 生の色、余白、角丸、影を画面ごとに増やさず、既存トークンを使う。
- 新しい見た目が再利用される場合、局所上書きではなく中央のvariantまたは共通部品にする。
- コンパクト化では文字を極端に縮める前に、不要な枠、カード、二重padding、空列、冗長な説明を整理する。
- カード、グラデーション、影、pill、装飾を同格に乱用せず、情報階層を優先する。
- アイコンは既存ライブラリまたは正しいSVGを使い、色、fill、stroke、配置を実画面で確認する。
- Tailwind、MUI、CSS Modulesなど特定方式を強制しない。既存方式を1つの正として使い、別方式を混在させない。

## 実ブラウザ確認

project付属のUI/E2E command、project dependency、local/global Playwright、installed browser、DevTools系tool、ローカルブラウザのheadless／CDPの順に、安全に使える経路を確認する。特定toolが常に存在すると仮定しない。共有browserが利用できないだけで視覚検証を打ち切らない。

Playwrightと対応browserが利用可能なら必ず実行する。変更したinteractionは開始状態から操作結果までを通し、hoverでは対象からcontrolへのpointer移動、double clickではnative event列、keyboard/touchでは対象input methodを再現する。screenshot生成、静止時の`scrollWidth`、bounding box、computed style、hit testだけで操作成功を代替しない。

プロジェクトの対応範囲を優先し、未定なら次を基準にする。

- mobile: `390x844`
- tablet／中間幅: `768x1024`
- desktop: `1280x800`
- wide: `1440x900`（意味がある場合）

関連する次の条件を確認する。

- 初期、入力済み、loading、成功、empty、error、disabled
- Light、Dark、System
- 長い日本語ラベルと現実的なデータ
- 未ログイン、ログイン済み
- keyboard navigation、focus、hover、クリック領域
- モーダル、メニュー、sticky要素、スクロール、非同期遷移
- ブレークポイント直前直後

各条件で確認する。

- clipping、overlap、意図しない横スクロール
- 主要アクションと視線誘導
- grid、端、baselineの整列
- 余白のリズムと情報密度
- 同格コントロールの一貫性
- モバイル時の情報優先順位
- focus、contrast、操作対象の識別性

`scrollWidth`、bounding box、computed styleなどの計測は有用だが、スクリーンショットの視覚確認を代替しない。

必要なら安定した画面だけvisual regression testへ追加する。意図を確認せずbaselineを更新しない。検証用画像はリポジトリの方針に従って保存し、一時画像を誤って公開・コミットしない。
