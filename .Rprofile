print("Loading .Rprofile...")
if (!"utils" %in% loadedNamespaces()) {
    library(utils)
}
if (file.exists("renv.lock")) {
    print("Activating renv...")
    source("renv/activate.R")
    
    # タイムアウト設定
    options(timeout = 3600)
    
    # BiocManagerの設定
    if (requireNamespace("BiocManager", quietly = TRUE)) {
        # BiocManagerの読み込み
        if (!"BiocManager" %in% loadedNamespaces()) {
            library(BiocManager)
        }
        
        # p3mミラーの設定
        options(
            BioC_mirror = "https://p3m.dev/bioconductor/latest",
            BIOCONDUCTOR_CONFIG_FILE = "https://p3m.dev/bioconductor/latest/config.yaml",
            repos = c(CRAN = "https://p3m.dev/cran/__linux__/bookworm/latest")
        )
        
        # BiocManagerのリポジトリ設定を適用
        options(repos = BiocManager::repositories())
    }
    
    # renvとpakの連携設定
    # pakをrenvのインストールエンジンとして設定
    if (requireNamespace("pak", quietly = TRUE)) {
        options(renv.config.install.function = function(pkgs, ...) {
            pak::pkg_install(pkgs, ask = FALSE, ...)
        })
        
        # pak用の設定
        options(
            pak.no_progress = FALSE,
            pak.suppress_startup = TRUE
        )
    }
}
print(".Rprofile loaded successfully.")
# 最後の行は無視されるのかもしれない