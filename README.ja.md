# ComfyUI-StringJoinTools

ComfyUI向けの、文字列結合と確認に特化したノードセットです。

## カテゴリ

`String Join Tools`

## 収録ノード

- Optional String Join (2)
- Optional String Join (3)
- Optional String Join (5)
- Optional String Join (10)
- Toggle String Join (2)
- Toggle String Join (3)
- Toggle String Join (5)
- Toggle String Join (10)
- Runtime Toggle String Join (2)
- Runtime Toggle String Join (3)
- Runtime Toggle String Join (5)
- Runtime Toggle String Join (10)
- String Output

## Optional String Join

- 番号付きのSTRING入力端子はすべてoptionalです。
- 未接続入力を無視します。
- 上流の供給ノードをBypassした結果、入力が欠落しても受け付けます。
- 完全な空文字列 `""` を無視します。
- 空白だけの文字列や、入力内の改行は保持します。
- 区切り文字は、有効な文字列同士の間だけに挿入します。
- すべての入力が未接続または空文字列なら `""` を返します。

入力数が足りない場合は、多段接続できます。

<img width="582" height="466" alt="image" src="https://github.com/user-attachments/assets/791980b1-8f51-49f0-ab20-06468d887cac" />

## 区切り文字のエスケープ

Optional版、Toggle版、Runtime Toggle版のすべてで、区切り文字に次の限定された
エスケープ記法を使用できます。

| 入力 | 実際の区切り文字 |
| --- | --- |
| `\n` | 改行（LF） |
| `\r\n` | Windows形式の改行（CRLF） |
| `\t` | タブ |
| `\\` | バックスラッシュ1文字 |
| `\\n` | 文字としての `\n` |

`\u`や`\x`など、表にない記法は変換せずそのまま保持します。

## Toggle String Join

入力数が2、3、5、10のバリエーションがあります。

接続した入力をボタンまたは入力行の左クリックでON/OFFできます。
選択状態と動作モードはキュー投入時に確定し、その後に画面上で変更しても
すでにキューへ積まれたジョブには影響しません。

大量のジョブを同じ構成で投入し、生成中は操作せずに運用したい場合に適しています。

<img width="540" height="598" alt="image" src="https://github.com/user-attachments/assets/8bfb37e7-c2f2-4cf4-91d7-d26ff40071ca" />

### 動作モード

- `multiple`: 各入力を独立してON/OFFできます。
- `single`: 0個または1個だけONにできます。

ノード下部には`QUEUE SNAPSHOT`と表示されます。

## Runtime Toggle String Join

大量の生成ジョブを先にキューへ積む運用を想定したノードです。
入力数が2、3、5、10のバリエーションがあります。

上流ノードは通常どおり各ジョブの実行時にSTRINGを生成します。
PromptRandomChoiceなどのランダム出力も、そのジョブで生成された値が
Runtime Toggle String Joinへ渡されます。

Joinノードが実行される瞬間に、ComfyUIサーバー上の最新モードと
トグル状態を参照し、その時点でONの非空文字列だけを結合します。

これにより、LoRA、Seed、キャラクターなどのジョブ固有設定を先に
大量投入しながら、生成途中でプロンプト構成だけを変更できます。

<img width="561" height="617" alt="image" src="https://github.com/user-attachments/assets/f9a37b43-5af4-444c-95fe-f63d6615e15a" />

### 動作モード

- `multiple`: 各入力を独立してON/OFFできます。
- `single`: 0個または1個だけONにできます。現在ONのボタンをもう一度
  押すと、すべてOFFになります。

Runtime版は背景が薄いアンバー色で表示され、ノード下部には`LIVE`と表示されます。

### 保存状態とライブ状態

次の値はワークフローへ保存されます。

- 動作モード
- 各入力のトグル状態
- 最後に選択した入力
- ノード固有のstate key

トグルまたはモードを変更すると、ワークフロー保存値とサーバー上の
ライブ状態を同時に更新します。すでにキューへ積まれた未実行ジョブも、
Join実行時に最新のライブ状態を参照します。

ライブ状態を取得できない場合は、キュー投入時の保存値を安全な
フォールバックとして使います。

### キャッシュ対策

サーバー状態には単調増加するrevisionを持たせています。
`IS_CHANGED`へrevisionを含め、ライブ変更後にJoin結果と後段処理が
キャッシュから誤って再利用されることを防ぎます。

### 反映タイミング

変更が反映されるのは、その変更後にRuntime Toggle String Joinが実行される
ジョブからです。通常の画像生成では「次の画像以降」と考えるのが安全です。

### JPEGコメントとの連携

実際に使われたプロンプトを画像ごとに残す場合は、同じ出力を
CLIP Text EncodeとImageSaverのJPEGコメント入力へ分岐してください。

### 複数タブについて

ライブ状態はstate keyを使ってComfyUIサーバー内で共有されます。
同じワークフローを複数タブから同時操作すると状態が競合するため、
操作用タブは原則1つにしてください。

## String Output

受け取った文字列、空文字列であること、文字数をノード内に表示します。
同じSTRINGをそのまま出力するため、処理途中へ挟んで確認できます。

<img width="356" height="270" alt="image" src="https://github.com/user-attachments/assets/8afa3b1a-3dfe-4a96-8791-b67c7d6fe3f1" />

## インストール

フォルダを次の場所へ展開してください。

`ComfyUI/custom_nodes/`

ComfyUIを再起動し、ブラウザを更新します。

追加のPythonパッケージは不要です。
<br/><br/><br/>

## 宣伝画像

<img width="1086" height="1448" alt="image" src="https://github.com/user-attachments/assets/71fd6415-259a-426e-9089-6965cb02aa89" />
