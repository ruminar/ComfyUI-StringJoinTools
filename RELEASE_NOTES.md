# Release Notes

## 0.1.0

ComfyUI向け文字列結合カスタムノード「String Join Tools」の初回リリースです。

### 収録ノード

- Optional String Join (2)
- Optional String Join (3)
- Optional String Join (5)
- Optional String Join (10)
- Runtime Toggle String Join (2)
- Runtime Toggle String Join (3)
- Runtime Toggle String Join (5)
- Runtime Toggle String Join (10)
- String Output

### Optional String Join

- 未接続のSTRING入力を無視して結合
- 上流ノードのBypassによって入力が欠落した場合にも対応
- 完全な空文字列を除外
- 空白のみの文字列と入力内の改行を保持
- 有効な文字列同士の間にだけ区切り文字を挿入
- すべての入力が未接続または空文字列の場合は空文字列を出力

### Runtime Toggle String Join

- キュー投入後でも、Join実行時の最新状態で各入力をON/OFF
- 入力数2、3、5、10のバリエーション
- 各入力を独立して切り替える`multiple`モード
- 0個または1個だけを有効にする`single`モード
- ボタンおよび入力行の左クリックによる切り替え
- OFF入力行をBypass風の紫色で表示
- クリック可能領域のホバー表示
- 入力・出力ソケット周辺の安全領域とドラッグ誤操作防止
- ワークフロー保存値を使った安全なフォールバック
- ライブ状態のrevisionを利用したキャッシュ無効化

### 区切り文字

全Optional版およびRuntime Toggle版で、次の限定的なエスケープ記法に対応します。

| 入力 | 実際の区切り文字 |
| --- | --- |
| `\n` | 改行（LF） |
| `\r\n` | Windows形式の改行（CRLF） |
| `\t` | タブ |
| `\\` | バックスラッシュ1文字 |
| `\\n` | 文字としての `\n` |

`\u`や`\x`など、未対応のエスケープ記法は変換せず保持します。

### String Output

- 入力文字列をノード内に表示
- 空文字列を明示的に確認可能
- 文字数を表示
- 受け取ったSTRINGをそのまま出力
- 入力が未接続の場合は空文字列として安全に処理

### 注意事項

- Runtime Toggle String Joinの変更は、その変更後にJoinノードが実行されるジョブから反映されます。
- ライブ状態はノードのstate keyを使ってComfyUIサーバー内に保持されます。
- 複製したワークフローが同じstate keyを保持している場合、複製元と複製先を同時に操作すると、最後に送信されたライブ状態で上書きされる可能性があります。

### 動作環境

- Python 3.9以降
- 追加のPythonパッケージなし
