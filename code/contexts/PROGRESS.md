# ObsClippingsManager v3.2.0 開発進捗管理

## 🎯 プロジェクト概要
**目標**: 学術研究における文献管理とMarkdownファイル整理を自動化する統合システムの一から再構築
**開発方針**: TDDアプローチ必須、仕様書完全準拠、**ワークフロー順実装**

**統合ワークフロー処理順序**:
```
organize → sync → fetch → section_parsing → ai_citation_support → enhanced-tagger → enhanced-translate → ochiai-format → final-sync
```

## 📊 開発進捗状況

### 🏗️ フェーズ1: 基盤システム完備（完了済み）
#### 1.1 プロジェクト構造・テスト環境
- [完了] 1.1.1 ディレクトリ構造作成（code/py/modules/以下）
- [完了] 1.1.2 __init__.py ファイル作成
- [完了] 1.1.3 依存関係管理（pyproject.toml, requirements.txt）
- [完了] 1.1.4 基本設定ファイル構造（config/config.yaml）
- [完了] 1.1.5 ユニットテスト基盤構築（code/unittest/）
- [完了] 1.1.6 テストユーティリティ作成
- [完了] 1.1.7 統合テスト仕様書作成（integrated_testing_specification.md）
- [完了] 1.1.8 統合テストシステム実装（code/integrated_test/, code/scripts/）
- [完了] 1.1.9 テストデータ管理システム

#### 1.2 共通基盤モジュール（shared）
- [完了] 1.2.1 ConfigManagerクラス設計・実装・テスト
- [完了] 1.2.2 IntegratedLoggerクラス設計・実装・テスト
- [完了] 1.2.3 ObsClippingsManagerError例外体系設計・実装・テスト
- [完了] 1.2.4 ユーティリティ機能（ファイルシステム、パス管理、バックアップ）
- [完了] 1.2.5 リトライ機構実装

#### 1.3 状態管理システム
- [完了] 1.3.1 YAMLHeaderProcessorクラス設計・実装・テスト
- [完了] 1.3.2 ProcessingStatusクラス設計・実装・テスト
- [完了] 1.3.3 状態チェック・スキップ条件判定ロジック実装
- [完了] 1.3.4 ヘッダー修復機能（--repair-headers）

#### 1.4 基盤システム統合テスト
- [完了] 1.4.1 基盤モジュール統合テスト実行
- [完了] 1.4.2 テスト環境完全分離確認
- [完了] 1.4.3 設定・ログ・例外処理連携確認

---

### 🔄 フェーズ2: ワークフロー機能実装（ワークフロー実行順）

#### 2.1 ステップ1: organize（ファイル整理）
- [完了] 2.1.1 FileOrganizerクラス設計・テスト作成
- [完了] 2.1.2 citation_keyディレクトリ作成機能実装
- [完了] 2.1.3 ファイル移動・リネーム機能実装
- [完了] 2.1.4 既存ファイル衝突回避機能実装
- [完了] 2.1.5 ユニットテスト実行・全テスト成功確認
- [] 2.1.6 **organize機能統合テスト実行**
  ```bash
  # organize機能の統合テスト（AI機能無効化）
  cd /home/user/proj/ObsClippingsManager
  uv run python code/scripts/run_integrated_test.py --test-type regression --specific-modules file_organizer --disable-ai-features --verbose
  ```

#### 2.2 ステップ2: sync（同期チェック）
- [ ] 2.2.1 SyncCheckerクラス設計・テスト作成
- [ ] 2.2.2 BibTeX ↔ Clippings整合性チェック実装
- [ ] 2.2.3 エッジケース検出機能実装
- [ ] 2.2.4 不整合レポート生成機能実装
- [ ] 2.2.5 自動修正提案機能実装
- [ ] 2.2.6 ユニットテスト実行・全テスト成功確認
- [ ] 2.2.7 **sync機能統合テスト実行**
  ```bash
  # sync機能の統合テスト（organize + sync）
  cd /home/user/proj/ObsClippingsManager
  uv run python code/scripts/run_integrated_test.py --test-type regression --specific-modules file_organizer,sync_checker --disable-ai-features --verbose
  ```

#### 2.3 ステップ3: fetch（引用文献取得）
- [ ] 2.3.1 BibTexParserクラス機能拡張（DOI抽出）
- [ ] 2.3.2 CitationFetcherクラス再設計・テスト作成
- [ ] 2.3.3 CrossRef API連携実装（10req/sec、品質閾値0.8）
- [ ] 2.3.4 Semantic Scholar API連携実装（1req/sec、品質閾値0.7）
- [ ] 2.3.5 OpenCitations API連携実装（5req/sec、最終フォールバック）
- [ ] 2.3.6 DataQualityEvaluatorクラス実装（品質スコア計算）
- [ ] 2.3.7 RateLimiterクラス実装（API別レート制限）
- [ ] 2.3.8 フォールバック制御ロジック実装
- [ ] 2.3.9 専用例外処理システム実装
- [ ] 2.3.10 CitationStatisticsクラス実装
- [ ] 2.3.11 references.bib生成機能実装
- [ ] 2.3.12 ユニットテスト実行・全テスト成功確認
- [ ] 2.3.13 **fetch機能統合テスト実行**
  ```bash
  # fetch機能の統合テスト（organize + sync + fetch）
  cd /home/user/proj/ObsClippingsManager
  uv run python code/scripts/run_integrated_test.py --test-type regression --specific-modules file_organizer,sync_checker,citation_fetcher --disable-ai-features --verbose
  ```

#### 2.4 ステップ4: section_parsing（セクション分割）
- [ ] 2.4.1 SectionParserクラス設計・テスト作成
- [ ] 2.4.2 Markdownヘッダー構造解析実装
- [ ] 2.4.3 セクション境界検出機能実装
- [ ] 2.4.4 ネストレベル管理実装
- [ ] 2.4.5 ユニットテスト実行・全テスト成功確認
- [ ] 2.4.6 **section_parsing機能統合テスト実行**
  ```bash
  # section_parsing機能の統合テスト（organize + sync + fetch + section_parsing）
  cd /home/user/proj/ObsClippingsManager
  uv run python code/scripts/run_integrated_test.py --test-type regression --specific-modules file_organizer,sync_checker,citation_fetcher,section_parser --disable-ai-features --verbose
  ```

#### 2.5 ステップ5: ai_citation_support（AI引用理解支援）
- [ ] 2.5.1 AICitationSupportクラス設計・テスト作成
- [ ] 2.5.2 Claude API連携基盤実装
- [ ] 2.5.3 references.bib内容YAMLヘッダー統合機能実装
- [ ] 2.5.4 引用文献情報統合機能実装
- [ ] 2.5.5 メタデータ自動生成実装
- [ ] 2.5.6 ユニットテスト実行・全テスト成功確認
- [ ] 2.5.7 **ai_citation_support機能統合テスト実行**
  ```bash
  # ai_citation_support機能の統合テスト（AI機能開始）
  cd /home/user/proj/ObsClippingsManager
  uv run python code/scripts/run_integrated_test.py --test-type regression --specific-modules file_organizer,sync_checker,citation_fetcher,section_parser,ai_citation_support --verbose
  ```

#### 2.6 ステップ6: enhanced-tagger（AIタグ生成）
- [ ] 2.6.1 AITaggingTranslationクラス設計・テスト作成
- [ ] 2.6.2 Claude 3.5 Haiku連携実装
- [ ] 2.6.3 自動タグ生成機能実装（バッチサイズ: 8）
- [ ] 2.6.4 YAMLヘッダータグ統合機能実装
- [ ] 2.6.5 品質評価・フィードバック機能実装
- [ ] 2.6.6 ユニットテスト実行・全テスト成功確認
- [ ] 2.6.7 **enhanced-tagger機能統合テスト実行**
  ```bash
  # enhanced-tagger機能の統合テスト
  cd /home/user/proj/ObsClippingsManager  
  uv run python code/scripts/run_integrated_test.py --test-type regression --specific-modules file_organizer,sync_checker,citation_fetcher,section_parser,ai_citation_support,ai_tagging_translation --verbose
  ```

#### 2.7 ステップ7: enhanced-translate（要約翻訳）
- [ ] 2.7.1 AITaggingTranslationクラス翻訳機能拡張
- [ ] 2.7.2 要約翻訳機能実装（バッチサイズ: 5）
- [ ] 2.7.3 翻訳品質評価機能実装
- [ ] 2.7.4 YAMLヘッダー翻訳結果統合実装
- [ ] 2.7.5 ユニットテスト実行・全テスト成功確認
- [ ] 2.7.6 **enhanced-translate機能統合テスト実行**
  ```bash
  # enhanced-translate機能の統合テスト
  cd /home/user/proj/ObsClippingsManager
  uv run python code/scripts/run_integrated_test.py --test-type regression --specific-modules file_organizer,sync_checker,citation_fetcher,section_parser,ai_citation_support,ai_tagging_translation --verbose
  ```

#### 2.8 ステップ8: ochiai-format（落合フォーマット要約）
- [ ] 2.8.1 OchiaiFormatクラス設計・テスト作成
- [ ] 2.8.2 6項目構造化要約生成実装（バッチサイズ: 3）
- [ ] 2.8.3 テンプレート管理システム実装
- [ ] 2.8.4 出力フォーマット管理実装
- [ ] 2.8.5 ユニットテスト実行・全テスト成功確認
- [ ] 2.8.6 **ochiai-format機能統合テスト実行**
  ```bash
  # ochiai-format機能の統合テスト
  cd /home/user/proj/ObsClippingsManager
  uv run python code/scripts/run_integrated_test.py --test-type regression --specific-modules file_organizer,sync_checker,citation_fetcher,section_parser,ai_citation_support,ai_tagging_translation,ochiai_format --verbose
  ```

#### 2.9 ステップ9: final-sync（最終同期）
- [ ] 2.9.1 最終同期機能設計・テスト作成
- [ ] 2.9.2 全処理結果最終バリデーション実装
- [ ] 2.9.3 状態更新・レポート生成実装
- [ ] 2.9.4 ユニットテスト実行・全テスト成功確認
- [ ] 2.9.5 **final-sync機能統合テスト実行**
  ```bash
  # final-sync機能の統合テスト（フェーズ2完了）
  cd /home/user/proj/ObsClippingsManager
  uv run python code/scripts/run_integrated_test.py --test-type full --verbose
  ```

---

### 🔧 フェーズ3: 統合ワークフローシステム

#### 3.1 IntegratedWorkflowクラス実装
- [ ] 3.1.1 IntegratedWorkflowクラス設計・テスト作成
- [ ] 3.1.2 処理ステップ順序管理実装
- [ ] 3.1.3 依存関係解決機能実装
- [ ] 3.1.4 エッジケース処理システム実装
- [ ] 3.1.5 ワークフロー実行制御実装
- [ ] 3.1.6 状態管理統合実装
- [ ] 3.1.7 ユニットテスト実行・全テスト成功確認
- [ ] 3.1.8 **IntegratedWorkflow統合テスト実行**
  ```bash
  # IntegratedWorkflowクラスの統合テスト
  cd /home/user/proj/ObsClippingsManager
  uv run python code/scripts/run_integrated_test.py --test-type full --verbose
  ```

#### 3.2 コマンドライン界面
- [ ] 3.2.1 CLIインターフェース設計・テスト作成
- [ ] 3.2.2 main.py実装（Click使用）
- [ ] 3.2.3 オプション管理実装（--dry-run, --force, --show-plan等）
- [ ] 3.2.4 プログレス表示機能実装
- [ ] 3.2.5 実行計画生成機能実装
- [ ] 3.2.6 ドライラン機能実装
- [ ] 3.2.7 エラー時の回復機能実装
- [ ] 3.2.8 実行結果レポート機能実装
- [ ] 3.2.9 ユニットテスト実行・全テスト成功確認
- [ ] 3.2.10 **CLI機能統合テスト実行**
  ```bash
  # CLI機能の統合テスト
  cd /home/user/proj/ObsClippingsManager
  uv run python code/scripts/run_integrated_test.py --test-type full --verbose
  ```

#### 3.3 統合ワークフロー統合テスト
- [ ] 3.3.1 **エンドツーエンド統合テスト実行**
  ```bash
  # 完全エンドツーエンド統合テスト
  cd /home/user/proj/ObsClippingsManager
  uv run python code/scripts/run_integrated_test.py --test-type full --reset-environment --verbose
  ```
- [ ] 3.3.2 全ワークフロー連携動作確認
  ```bash
  # 全ワークフロー連携確認
  cd /home/user/proj/ObsClippingsManager
  uv run python code/scripts/run_integrated_test.py --test-type full --verbose --report-format html
  ```
- [ ] 3.3.3 AI機能統合動作確認
  ```bash
  # AI機能統合動作確認
  cd /home/user/proj/ObsClippingsManager
  uv run python code/scripts/run_integrated_test.py --test-type regression --specific-modules ai_citation_support,ai_tagging_translation,ochiai_format --verbose
  ```
- [ ] 3.3.4 エッジケース処理動作確認
  ```bash
  # エッジケース処理確認（環境リセット）
  cd /home/user/proj/ObsClippingsManager
  uv run python code/scripts/run_integrated_test.py --test-type full --reset-environment --keep-environment --verbose
  ```
- [ ] 3.3.5 パフォーマンステスト実行
  ```bash
  # パフォーマンステスト実行
  cd /home/user/proj/ObsClippingsManager
  uv run python code/scripts/run_integrated_test.py --test-type performance --verbose --report-format html
  ```

---

### 🧪 フェーズ4: 最終品質保証・リリース準備

#### 4.1 包括的テスト
- [ ] 4.1.1 全モジュールのテストカバレッジ100%達成
- [ ] 4.1.2 エッジケーステスト追加
- [ ] 4.1.3 モックとスタブの最適化
- [ ] 4.1.4 テスト実行速度最適化
- [ ] 4.1.5 複数環境でのテスト実行

#### 4.2 品質保証
- [ ] 4.2.1 コード品質メトリクス確認
- [ ] 4.2.2 パフォーマンステスト実施
- [ ] 4.2.3 セキュリティ検証
- [ ] 4.2.4 メモリ使用量確認

#### 4.3 ドキュメント・リリース準備
- [ ] 4.3.1 README.md最終更新
- [ ] 4.3.2 仕様書整合性確認
- [ ] 4.3.3 API ドキュメント生成
- [ ] 4.3.4 トラブルシューティングガイド更新
- [ ] 4.3.5 リリース準備完了確認

---

## 🚨 課題・リスク管理

### 技術的課題
- [ ] 三段階フォールバックAPI レート制限協調動作
- [ ] Semantic Scholar API キー管理
- [ ] データ品質評価精度向上
- [ ] 大量ファイル処理パフォーマンス
- [ ] YAMLヘッダー破損対応
- [ ] 複雑な依存関係管理

### 開発プロセス課題
- [ ] 各ステップ統合テスト品質確保
- [ ] API統合テスト環境構築
- [ ] テスト実行時間最適化
- [ ] モジュール間インターフェース設計
- [ ] エラー処理統一性確保
- [ ] ドキュメント同期維持

## 📝 開発メモ

### 重要な開発原則
1. **ワークフロー順実装**: organize → sync → fetch → ... の順序で実装
2. **段階的統合テスト**: 各ステップ完了後に統合テスト実行必須
3. **依存関係の方向**: shared ← workflow_steps ← integrated_workflow ← main
4. **状態管理**: 全処理ステップでYAMLヘッダー更新必須
5. **エラー処理**: ObsClippingsManagerError基底の統一例外体系
6. **テスト分離**: `/tmp/ObsClippingsManager_Test` での完全分離

### 統合テスト実行タイミング
```bash
# 各ステップ完了後に実行
cd /home/user/proj/ObsClippingsManager
uv run code/unittest/run_all_tests.py

# 統合テスト実行
uv run python code/integrated_test/run_integrated_tests.py
```

## 📋 統合テスト実行ガイド

### 統合テストの種類と使い分け

#### 1. **regressionテスト** - 段階的統合テスト
各モジュール完成後に実行する基本的な統合テスト。特定モジュールとその依存関係を検証。

```bash
# 基本形式
uv run python code/scripts/run_integrated_test.py --test-type regression --specific-modules [モジュール名] --verbose

# AI機能実装前（2.1～2.4）
--disable-ai-features フラグを追加

# AI機能実装後（2.5～2.9）
--disable-ai-features フラグを削除
```

#### 2. **fullテスト** - 完全統合テスト
大きなマイルストーン完了時や最終検証時に実行。全ワークフローの完全なエンドツーエンド検証。

```bash
# フェーズ完了時の完全テスト
uv run python code/scripts/run_integrated_test.py --test-type full --verbose

# 環境リセット後の完全テスト（推奨）
uv run python code/scripts/run_integrated_test.py --test-type full --reset-environment --verbose
```

#### 3. **performanceテスト** - パフォーマンス検証
システム完成時やパフォーマンス課題調査時に実行。

```bash
# パフォーマンステスト
uv run python code/scripts/run_integrated_test.py --test-type performance --verbose --report-format html
```

### 主要オプション解説

| オプション | 用途 | 推奨使用場面 |
|------------|------|--------------|
| `--test-type regression` | 特定モジュールの統合テスト | 各モジュール完成後 |
| `--test-type full` | 完全エンドツーエンド検証 | フェーズ完了時 |
| `--test-type performance` | パフォーマンス測定 | 最終検証時 |
| `--specific-modules` | テスト対象モジュール指定 | 段階的テスト実行 |
| `--disable-ai-features` | AI機能無効化 | AI実装前テスト |
| `--reset-environment` | テスト環境強制リセット | 環境問題解決時 |
| `--keep-environment` | テスト環境保持 | デバッグ時 |
| `--verbose` | 詳細ログ出力 | 問題調査時 |
| `--report-format html` | HTML形式レポート | 詳細結果確認時 |

### モジュール名対応表

| ワークフローステップ | モジュール名 |
|---------------------|--------------|
| organize | `file_organizer` |
| sync | `sync_checker` |
| fetch | `citation_fetcher` |
| section_parsing | `section_parser` |
| ai_citation_support | `ai_citation_support` |
| enhanced-tagger | `ai_tagging_translation` |
| enhanced-translate | `ai_tagging_translation` |
| ochiai-format | `ochiai_format` |
| final-sync | `final_sync` |

### デバッグ時の統合テスト

```bash
# デバッグモード（環境保持、詳細ログ）
uv run python code/scripts/run_integrated_test.py --test-type regression --specific-modules [モジュール名] --keep-environment --verbose

# 特定の問題調査時
uv run python code/scripts/run_integrated_test.py --test-type full --reset-environment --keep-environment --verbose --report-format html
```

### 統合テスト失敗時の対応

1. **ユニットテスト確認**
   ```bash
   uv run code/unittest/run_all_tests.py
   ```

2. **環境リセット後再実行**
   ```bash
   uv run python code/scripts/run_integrated_test.py --reset-environment [元のオプション]
   ```

3. **デバッグモードで詳細確認**
   ```bash
   uv run python code/scripts/run_integrated_test.py --keep-environment --verbose [元のオプション]
   ```

4. **ログ確認**
   - 統合テストログ: テスト実行時に表示
   - アプリケーションログ: `logs/obsclippings.log`

### API連携注意事項
- **CrossRef**: 秒間10リクエスト制限、品質閾値0.8
- **Semantic Scholar**: 秒間1リクエスト制限（API キー使用）、品質閾値0.7
- **OpenCitations**: 秒間5リクエスト制限、最終フォールバック
- **Claude API**: 使用量制限確認必須、バッチ処理最適化

### 品質保証チェックリスト
- [ ] 各ステップのユニットテスト100%成功
- [ ] 各ステップの統合テスト成功
- [ ] 全テスト実行成功後のGitコミット・プッシュ
- [ ] 進捗状況のPROGRESS.md更新
