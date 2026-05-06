※日本語は英語の後にあります。／Japanese version below.

# Job Stream Linear

## Overview
**Job Stream Linear** is an application designed to improve job search efficiency by reducing the time spent reviewing and evaluating job postings.

Job listings often contain extensive requirements and varying formats, making it tedious to assess eligibility. This tool streamlines the process into a more linear workflow by handling the heavy lifting, allowing users to focus on final decision-making.

This project is intended for personal productivity and learning purposes only.
It does not automate job applications or violate platform terms of service.

---

## Features

- Automated job search via Adzuna API  
- Semi-automated matching workflow comparing job requirements with user profiles  
- Keyword filtering to eliminate irrelevant listings  
- Match scoring system with actionable improvement suggestions  
- AI-generated job summaries  
- Tailored cover letter generation using a local LLM  
- Skill trend tracking to analyse market demand  
- Resource optimisation to minimise unnecessary LLM calls  

---

## Future Improvements

- Investigate the feasibility of using Gemma 4 for improved Japanese prompt handling (compared to Gemma 3, which defaults to English).  
- Implement scheduled skill normalisation to standardise varied terminology across job postings.  
- Further visualised analytic tools

---

## Change Log

### 06/05/2026
- Organised into folders
- Default cover letter prompt implemented
- Redesigned Readme
- Added Japanese Readme section

### 02/05/2026
- Manual mode implemented  

### 01/05/2026
- Auto mode completed  
- Revised Mode 2 (HTML to TXT) for improved adaptability  

### 12/03/2026
- Converted `.txt` files to proper `.json` format  

### 10/03/2026
- Skill keyword normalisation prototype  
- Implemented skill statistics tracking  
- Integrated cover letter generation into main workflow  

### 09/03/2026
- Converted `personal_profile.txt` to JSON  
- Added cover letter generation  
- Consolidated job data into `job_json.txt`  

### 08/03/2026
- Added LLM scoring and suggestions  
- Restructured into batch processing  
- Improved output formatting  

### 07/03/2026
- Automated comparison of user skills vs job requirements  

### 06/03/2026
- Refactored and modularised workflow  

### 04/03/2026
- Introduced job class structure  
- Planned multi-mode support  
- Optimised LLM calls  

### 27/02/2026
- Prototype filters (non-decision keywords and experience years)  
- Pagination support  

### 25/02/2026
- Initial commit  

---

## Requirements

- Adzuna API for automated job searching  
- Ollama for running the local LLM  

---

## Workflow Overview

1. Retrieve job postings (Auto mode via Adzuna or Manual mode)  
2. Check records to prevent duplication  
3. Apply resource optimisation filtering before invoking the LLM:  
   - Title  
   - Company  
   - Location  
   - Date posted  
   - Contract type  
   - Job type  
   - Experience requirements  
4. Use a local LLM to:  
   - Generate summaries  
   - Calculate match scores  
   - Provide improvement suggestions  
5. Present user options:  
   - Pass  
   - Bookmark  
   - Generate tailored cover letter  
6. Proceed to the next job posting  

---

## Setup Instructions

Prepare the following files before running the application:

- `personal_profiles.json`  
  Contains user profile and skills. Skills should be updated progressively as normalisation improves  

- `word-list`  
  Keywords to filter out unwanted jobs  

- `prompts` and `signature`  
  Default templates for cover letter generation (customisable)  

- `param.txt`  
  Contains Adzuna App ID and API Key (required for Auto mode)  

---

## Usage

### Auto Mode

1. Complete setup  
2. Enter search keywords  
3. Wait for job results  
4. Review summaries and make decisions  
5. Continue to next listing  

---

### Manual Mode

1. Complete setup  
2. Paste job description into `content.txt`  
3. Select Manual Mode (Option 2)  
4. Review summary and make decision  

---

## Project Structure

```
.
├── output_txt/
│   └── cover_letter.txt        # Generated cover letters
│
├── prompt/                     # default prompt will be used if empty
│   ├── prompt_p1.txt           # Prompt part 1
│   ├── prompt_p2.txt           # Prompt part 2
│   ├── prompt_p3.txt           # Prompt part 3
│   ├── prompt_p4.txt           # Prompt part 4
│   └── signature.txt           # Signature
│
├── temp/
│   ├── bookmarks.txt           # Temporary bookmarks storage
│   ├── job.json                # Temporary job data
│   └── pass_list.txt           # Filtered job list
│
├── words_filter/
│   ├── fluff_words.txt         # Words to avoid (fluff)
│   ├── non_prefered_words.txt  # Non-preferred wording
│   └── seniority_words.txt     # Seniority-related filters
│
├── .gitignore                  
├── content.txt                 # Core content input
├── jobObj.py                   
├── llm.py                      # LLM interaction logic
├── main.py                     # Entry point
├── param.txt                   # Adzuna parameters
├── personal_profile.json       # User profile data
├── readme.md                   
├── skills_stats.json           # Skill frequency data
└── util.py                     
```



# Job Stream Linear

## 概要
**Job Stream Linear** は、求人情報の確認・評価にかかる時間を削減し、就職活動の効率を向上させるために設計されたアプリです。

求人情報には多くの要件や様々な書き方が含まれていることが多く、応募の判断に時間がかかります。本ツールはそのプロセスを簡略化し、ユーザーを応募する過程をリニア化するアプリです。

本プロジェクトは、個人の生産性向上および学習目的のみを意図しています。  
求人応募の自動化や、各プラットフォームの利用規約に違反する行為は行いません。

---

## 主な機能

- Adzuna APIを利用した求人検索の自動化
- 求人要件とユーザープロフィールを比較する半自動マッチング機能  
- 不要な求人を除外するキーワードフィルタリング  
- 改善提案付きのマッチスコアリングシステム  
- AIによる求人要約生成  
- ローカルLLMを使用したカスタマイズされたカバーレター生成  
- スキルトレンドの追跡による市場需要の分析  
- 不要なLLM呼び出しを最小化するリソース最適化  

---

## 今後の改善点

- Gemma 4を使用した日本語プロンプト処理の改善可能性の検証（英語に偏るGemma 3との比較）  
- 求人情報間で異なる用語を統一するためのスキル正規化の定期実行  
- 分析機能のさらなる可視化  

---

## 更新履歴

### 06/05/2026
- フォルダ構成の整理
- デフォルトの就職書類プロンプトを実装
- READMEの書き直し

### 02/05/2026
- マニュアルモードを実装  

### 01/05/2026
- 自動モードを完成  
- Mode 2（HTML → TXT）を改良し柔軟性を向上  

### 12/03/2026
- `.txt` ファイルを `.json` 形式に変換  

### 10/03/2026
- スキルキーワード正規化のプロトタイプ  
- スキル統計トラッキングの実装
- 就職書類生成をメインワークフローに統合  

### 09/03/2026
- `personal_profile.txt` をJSONに変換  
- カバーレター生成機能を追加  
- 求人データを `job_json.txt` に統合  

### 08/03/2026
- LLMによるスコアリングと改善提案を追加  
- バッチ処理構造に書き直し  
- 出力フォーマットを改善  

### 07/03/2026
- ユーザースキルと求人要件の自動比較を実装  

### 06/03/2026
- ワークフローのリファクタリングとモジュール化  

### 04/03/2026
- Jobクラス構造を導入  
- マルチモード対応を計画  
- LLM呼び出しの最適化  

### 27/02/2026
- フィルタプロトタイプ（非決定キーワード・経験年数）  
- ページネーション対応  

### 25/02/2026
- 初回コミット  

---

## 必要要件

- Adzuna API（求人検索の自動化用）  
- Ollama（ローカルLLM実行用）  

---

## ワークフロー概要

1. 求人情報を取得（Adzunaによる自動モード、または手動モード）  
2. 重複防止のため既存データをチェック  
3. LLM実行前にリソース最適化フィルタを適用：  
   - 職種名  
   - 企業名  
   - 勤務地  
   - 投稿日  
   - 契約形態  
   - 雇用形態  
   - 経験要件  
4. ローカルLLMを使用して以下を実行：  
   - 要約生成  
   - マッチスコア算出  
   - 改善提案の提示  
5. ユーザー操作の選択：  
   - スキップ  
   - ブックマーク  
   - カスタマイズされたカバーレター生成  
6. 次の求人へ進む  

---

## セットアップ手順

アプリケーション実行前に以下のファイルを準備してください：

- `personal_profiles.json`  
  ユーザープロフィールおよびスキル情報を格納（正規化の進行に応じて随時更新）  

- `word-list`  
  不要な求人を除外するためのキーワード  

- `prompts` および `signature`  
  カバーレター生成用のデフォルトテンプレート（カスタマイズ可能）  

- `param.txt`  
  AdzunaのApp IDおよびAPIキー（自動モードに必要）  

---

## 使用方法

### 自動モード

1. セットアップを完了  
2. 検索キーワードを入力  
3. 求人結果を待機  
4. 要約を確認し意思決定  
5. 次の求人へ進む  

---

### マニュアルモード

1. セットアップを完了  
2. 求人内容を `content.txt` に貼り付け  
3. マニュアルモード（オプション2）を選択  
4. 要約を確認し意思決定  

---

## プロジェクト構成

```

.
├── output_txt/
│   └── cover_letter.txt        # 生成されたカバーレター
│
├── prompt/                     # 空の場合はデフォルトプロンプトを使用
│   ├── prompt_p1.txt           # プロンプトパート1
│   ├── prompt_p2.txt           # プロンプトパート2
│   ├── prompt_p3.txt           # プロンプトパート3
│   ├── prompt_p4.txt           # プロンプトパート4
│   └── signature.txt           # 署名
│
├── temp/
│   ├── bookmarks.txt           # 一時ブックマーク保存
│   ├── job.json                # 一時求人データ
│   └── pass_list.txt           # フィルタ済み求人リスト
│
├── words_filter/
│   ├── fluff_words.txt         # 不要語（装飾語）
│   ├── non_prefered_words.txt  # 非推奨表現
│   └── seniority_words.txt     # 役職レベルフィルタ
│
├── .gitignore
├── content.txt                 # 入力用コンテンツ
├── jobObj.py
├── llm.py                      # LLM処理ロジック
├── main.py                     # エントリーポイント
├── param.txt                   # Adzuna設定
├── personal_profile.json       # ユーザープロフィール
├── readme.md
├── skills_stats.json           # スキル頻度データ
└── util.py

```
