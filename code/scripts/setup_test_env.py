#!/usr/bin/env python3
"""
TestManuscripts環境構築スクリプト

本番環境(/home/user/ManuscriptsManager)からテストデータをコピーし、
テスト用の初期状態を作成・管理します。
"""

import os
import shutil
import sys
from pathlib import Path
from datetime import datetime
import argparse

def setup_test_environment(source_dir: str = "/home/user/ManuscriptsManager", 
                          test_dir: str = "/home/user/proj/ObsClippingsManager/TestManuscripts"):
    """
    テスト環境をセットアップ
    
    Args:
        source_dir: 本番環境のパス
        test_dir: テスト環境のパス
    """
    source_path = Path(source_dir)
    test_path = Path(test_dir)
    
    print(f"🚀 Setting up test environment...")
    print(f"   Source: {source_path}")
    print(f"   Target: {test_path}")
    
    # 1. テストディレクトリの作成
    if test_path.exists():
        print(f"⚠️  Test directory already exists: {test_path}")
        response = input("   Remove existing directory? (y/N): ")
        if response.lower() == 'y':
            shutil.rmtree(test_path)
            print(f"   Removed existing directory")
        else:
            print(f"   Keeping existing directory")
            return False
    
    test_path.mkdir(parents=True, exist_ok=True)
    
    # 2. CurrentManuscript.bibのコピー
    source_bib = source_path / "CurrentManuscript.bib"
    target_bib = test_path / "CurrentManuscript.bib"
    
    if source_bib.exists():
        shutil.copy2(source_bib, target_bib)
        print(f"✅ Copied BibTeX file: {target_bib}")
    else:
        print(f"⚠️  Source BibTeX file not found: {source_bib}")
        # サンプルBibTeXファイルを作成
        create_sample_bibtex(target_bib)
        print(f"✅ Created sample BibTeX file: {target_bib}")
    
    # 3. Clippingsディレクトリのコピー
    source_clippings = source_path / "Clippings"
    target_clippings = test_path / "Clippings"
    
    if source_clippings.exists():
        shutil.copytree(source_clippings, target_clippings)
        print(f"✅ Copied Clippings directory: {target_clippings}")
    else:
        print(f"⚠️  Source Clippings directory not found: {source_clippings}")
        # サンプルClippingsディレクトリを作成
        create_sample_clippings(target_clippings)
        print(f"✅ Created sample Clippings directory: {target_clippings}")
    
    # 4. バックアップ情報ファイルの作成
    backup_info = test_path / ".test_env_info.txt"
    with open(backup_info, 'w', encoding='utf-8') as f:
        f.write(f"Test Environment Setup Information\n")
        f.write(f"==================================\n")
        f.write(f"Setup Date: {datetime.now().isoformat()}\n")
        f.write(f"Source Directory: {source_path}\n")
        f.write(f"Test Directory: {test_path}\n")
        f.write(f"BibTeX File: {target_bib}\n")
        f.write(f"Clippings Directory: {target_clippings}\n")
        f.write(f"\n")
        f.write(f"Reset Command:\n")
        f.write(f"python code/scripts/setup_test_env.py --reset\n")
    
    print(f"✅ Created backup info: {backup_info}")
    print(f"")
    print(f"🎉 Test environment setup completed!")
    print(f"")
    print(f"Test with:")
    print(f"  PYTHONPATH=code/py uv run python code/py/main.py run-integrated --workspace {test_path}")
    
    return True

def create_sample_bibtex(target_file: Path):
    """
    サンプルBibTeXファイルを作成
    """
    sample_content = """@article{smith2023test,
    title = {Example Paper: Advanced Machine Learning Techniques},
    author = {Smith, John and Jones, Mary and Wilson, Robert},
    year = {2023},
    doi = {10.1000/example.2023.001},
    journal = {Journal of Example Research},
    volume = {42},
    number = {1},
    pages = {123--145},
    publisher = {Example Publisher}
}

@article{jones2024neural,
    title = {Neural Networks in Biological Data Analysis: A Comprehensive Review},
    author = {Jones, Alice and Brown, David},
    year = {2024},
    doi = {10.1000/neural.2024.002},
    journal = {Computational Biology Review},
    volume = {15},
    number = {3},
    pages = {45--78},
    publisher = {Science Publications}
}

@article{wilson2023deep,
    title = {Deep Learning Applications in Medical Imaging},
    author = {Wilson, Sarah and Davis, Michael and Taylor, Emma},
    year = {2023},
    doi = {10.1000/medical.2023.003},
    journal = {Medical AI Journal},
    volume = {8},
    number = {2},
    pages = {234--267},
    publisher = {Medical Press}
}

@article{brown2024quantum,
    title = {Quantum Computing for Protein Folding Prediction},
    author = {Brown, Peter and Clark, Lisa},
    year = {2024},
    doi = {10.1000/quantum.2024.004},
    journal = {Quantum Biology},
    volume = {3},
    number = {1},
    pages = {12--34},
    publisher = {Future Science}
}

@article{davis2023genomics,
    title = {Genomics Data Processing with Cloud Computing},
    author = {Davis, Jennifer and Miller, Thomas},
    year = {2023},
    doi = {10.1000/genomics.2023.005},
    journal = {Genomics & Cloud Computing},
    volume = {12},
    number = {4},
    pages = {89--112},
    publisher = {Tech Publications}
}
"""
    
    target_file.parent.mkdir(parents=True, exist_ok=True)
    with open(target_file, 'w', encoding='utf-8') as f:
        f.write(sample_content)

def create_sample_clippings(target_dir: Path):
    """
    サンプルClippingsディレクトリを作成
    """
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # サンプル論文ファイルを作成
    sample_papers = [
        {
            "filename": "smith2023test.md",
            "content": """# Smith et al. (2023) - Example Paper: Advanced Machine Learning Techniques

## Abstract
This paper presents advanced machine learning techniques for data analysis. The study demonstrates significant improvements in accuracy and efficiency compared to traditional methods.

## Key Points
- Novel deep learning architecture
- 95% accuracy improvement
- Reduced computational complexity
- Real-world applications validated

## Methodology
The research employs a hybrid approach combining convolutional neural networks with transformer architectures.

## Results
Results show significant performance gains across multiple benchmarks.

## References
[1] Previous work on ML techniques
[2] Baseline comparison studies
[3] Related deep learning research
"""
        },
        {
            "filename": "jones2024neural.md", 
            "content": """# Jones et al. (2024) - Neural Networks in Biological Data Analysis: A Comprehensive Review

## Abstract
A comprehensive review of neural network applications in biological data analysis, covering recent advances and future directions.

## Key Topics
- Sequence analysis
- Protein structure prediction
- Gene expression analysis
- Drug discovery applications

## Current Challenges
- Data heterogeneity
- Interpretability issues
- Computational requirements
- Validation standards

## Future Directions
The field is moving towards more interpretable models and standardized evaluation metrics.
"""
        },
        {
            "filename": "wilson2023deep.md",
            "content": """# Wilson et al. (2023) - Deep Learning Applications in Medical Imaging

## Abstract
This study explores deep learning applications in medical imaging, focusing on diagnostic accuracy and clinical implementation.

## Applications
- X-ray analysis
- MRI scan interpretation
- CT scan processing
- Pathology image analysis

## Clinical Impact
Improved diagnostic accuracy by 25% compared to traditional methods.

## Implementation
Successfully deployed in 5 medical centers with positive feedback from radiologists.
"""
        }
    ]
    
    for paper in sample_papers:
        paper_file = target_dir / paper["filename"]
        with open(paper_file, 'w', encoding='utf-8') as f:
            f.write(paper["content"])

def reset_test_environment(test_dir: str = "/home/user/proj/ObsClippingsManager/TestManuscripts"):
    """
    テスト環境を初期状態にリセット
    """
    test_path = Path(test_dir)
    
    if not test_path.exists():
        print(f"❌ Test environment not found: {test_path}")
        return False
    
    # バックアップ情報の確認
    backup_info = test_path / ".test_env_info.txt"
    if backup_info.exists():
        print(f"📋 Found test environment info:")
        with open(backup_info, 'r', encoding='utf-8') as f:
            print(f"   {f.read()}")
    
    print(f"🔄 Resetting test environment...")
    
    # 処理済みファイル・ディレクトリの削除
    clippings_dir = test_path / "Clippings"
    if clippings_dir.exists():
        # Citation keyディレクトリの削除（整理処理により作成されたもの）
        for item in clippings_dir.iterdir():
            if item.is_dir():
                print(f"   Removing citation key directory: {item.name}")
                shutil.rmtree(item)
        
        # サンプルファイルの復元
        create_sample_clippings(clippings_dir)
        print(f"✅ Reset Clippings directory to initial state")
    
    # BibTeXファイルも初期状態に復元
    bibtex_file = test_path / "CurrentManuscript.bib"
    if bibtex_file.exists():
        create_sample_bibtex(bibtex_file)
        print(f"✅ Reset BibTeX file to initial state")
    
    print(f"")
    print(f"🎉 Test environment reset completed!")
    print(f"")
    print(f"Ready for testing with:")
    print(f"  PYTHONPATH=code/py uv run python code/py/main.py run-integrated --workspace {test_path}")
    
    return True

def main():
    parser = argparse.ArgumentParser(description="Test environment setup and management")
    parser.add_argument('--reset', action='store_true', help='Reset test environment to initial state')
    parser.add_argument('--source', default="/home/user/ManuscriptsManager", 
                       help='Source directory (default: /home/user/ManuscriptsManager)')
    parser.add_argument('--test-dir', default="/home/user/proj/ObsClippingsManager/TestManuscripts",
                       help='Test directory (default: ./TestManuscripts)')
    
    args = parser.parse_args()
    
    try:
        if args.reset:
            success = reset_test_environment(args.test_dir)
        else:
            success = setup_test_environment(args.source, args.test_dir)
        
        if success:
            sys.exit(0)
        else:
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 