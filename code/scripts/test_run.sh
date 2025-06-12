#!/bin/bash
# ObsClippingsManager v3.0 テスト実行スクリプト

set -e  # エラー時に停止

# 設定
PROJECT_ROOT="/home/user/proj/ObsClippingsManager"
TEST_WORKSPACE="$PROJECT_ROOT/TestManuscripts"

# 色付きメッセージ
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

echo_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

echo_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# ヘルプ表示
show_help() {
    cat << EOF
ObsClippingsManager v3.0 テスト実行スクリプト

使用方法:
    $0 [オプション]

オプション:
    --setup         テスト環境をセットアップ
    --reset         テスト環境をリセット
    --run           テスト実行（デフォルト）
    --dry-run       ドライラン実行
    --plan          実行計画表示
    --debug         デバッグモードで実行
    --help, -h      このヘルプを表示

例:
    $0                    # 基本テスト実行
    $0 --reset --run      # リセット後テスト実行
    $0 --dry-run          # ドライラン実行
    $0 --debug            # デバッグモード実行

EOF
}

# テスト環境セットアップ
setup_test_env() {
    echo_info "テスト環境をセットアップしています..."
    cd "$PROJECT_ROOT"
    python code/scripts/setup_test_env.py
    echo_info "テスト環境セットアップ完了"
}

# テスト環境リセット
reset_test_env() {
    echo_info "テスト環境をリセットしています..."
    cd "$PROJECT_ROOT"
    echo "y" | python code/scripts/setup_test_env.py --reset
    echo_info "テスト環境リセット完了"
}

# テスト実行
run_test() {
    local mode="$1"
    
    cd "$PROJECT_ROOT"
    
    # テスト環境の存在確認
    if [ ! -d "$TEST_WORKSPACE" ]; then
        echo_warn "テスト環境が見つかりません。セットアップを実行します..."
        setup_test_env
    fi
    
    echo_info "テスト実行開始: $mode"
    echo_info "ワークスペース: $TEST_WORKSPACE"
    
    case "$mode" in
        "run")
            PYTHONPATH=code/py uv run python code/py/main.py \
                run-integrated --workspace "$TEST_WORKSPACE" \
                --enable-tagger --enable-translate-abstract
            ;;
        "dry-run")
            PYTHONPATH=code/py uv run python code/py/main.py \
                --dry-run --verbose \
                run-integrated --workspace "$TEST_WORKSPACE" \
                --enable-tagger --enable-translate-abstract
            ;;
        "plan")
            PYTHONPATH=code/py uv run python code/py/main.py \
                run-integrated --workspace "$TEST_WORKSPACE" --show-plan \
                --enable-tagger --enable-translate-abstract
            ;;
        "debug")
            PYTHONPATH=code/py uv run python code/py/main.py \
                --log-level debug --verbose \
                run-integrated --workspace "$TEST_WORKSPACE" \
                --enable-tagger --enable-translate-abstract
            ;;
        *)
            echo_error "不明なモード: $mode"
            exit 1
            ;;
    esac
    
    echo_info "テスト実行完了"
}

# テスト結果確認
show_test_results() {
    echo_info "テスト結果確認:"
    echo "----------------------------------------"
    echo "テスト環境情報:"
    if [ -f "$TEST_WORKSPACE/.test_env_info.txt" ]; then
        cat "$TEST_WORKSPACE/.test_env_info.txt"
    else
        echo_warn "テスト環境情報ファイルが見つかりません"
    fi
    
    echo ""
    echo "Clippingsディレクトリ構造:"
    if [ -d "$TEST_WORKSPACE/Clippings" ]; then
        ls -la "$TEST_WORKSPACE/Clippings/"
    else
        echo_warn "Clippingsディレクトリが見つかりません"
    fi
    echo "----------------------------------------"
}

# メイン処理
main() {
    local action="run"
    
    # 引数解析
    while [[ $# -gt 0 ]]; do
        case $1 in
            --setup)
                setup_test_env
                exit 0
                ;;
            --reset)
                reset_test_env
                shift
                # 次の引数をチェック
                if [[ $# -eq 0 ]]; then
                    exit 0
                fi
                ;;
            --run)
                action="run"
                shift
                ;;
            --dry-run)
                action="dry-run"
                shift
                ;;
            --plan)
                action="plan"
                shift
                ;;
            --debug)
                action="debug"
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                echo_error "不明なオプション: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # テスト実行
    run_test "$action"
    
    # 結果表示
    show_test_results
}

# スクリプト実行
main "$@" 