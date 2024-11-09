To install:

```bash
virtualenv venv
source venv/bin/activate
pip install -r requirements.txt
```

To run:
```bash
cd crawler
scrapy crawl kb -o output.jsonl -t jsonlines
```

Relevant file:
`kb_crawler/spiders/kb_spider.py`
