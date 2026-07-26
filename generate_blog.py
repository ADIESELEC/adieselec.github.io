name: Auto-generate weekly blog post
 
on:
  schedule:
    # Every Monday at 08:00 UTC (10:00 SAST)
    - cron: '0 8 * * 1'
  # Allows manually triggering a run from the Actions tab for testing
  workflow_dispatch:
 
permissions:
  contents: write
 
jobs:
  generate-blog-post:
    runs-on: ubuntu-latest
 
    steps:
      - name: Check out repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 0
 
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
 
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
 
      - name: Verify GEMINI_API_KEY secret is set
        env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
        run: |
          if [ -z "$GEMINI_API_KEY" ]; then
            echo "ERROR: GEMINI_API_KEY secret is not set in repository settings."
            echo "Go to Settings > Secrets and variables > Actions and add it."
            exit 1
          fi
          echo "GEMINI_API_KEY is present."
 
      - name: Generate blog post
        env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
        run: python generate_blog.py
 
      - name: Commit and push new blog post
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add blog/
          if git diff --cached --quiet; then
            echo "No new blog post generated, nothing to commit."
          else
            git commit -m "Auto-generate weekly blog post [skip ci]"
            git push
          fi
 
