# Extraction spot-check (human review)

_Generated 2026-11-25 from `C:\Users\asusj\.github-tool\github-tool.db`._

Sampled **46 repositories** and **184 install commands**; **3** commands sit near caution words (for example / e.g. / alternative / deprecated). This is the optional independent human spot-check from the roadmap (Phase 6). The automated source-line check and an agent semantic review already passed; this packet is for a person to confirm semantic trustworthiness on a sample.

## How to review

1. For each repository, open the GitHub URL.
2. For each command, read the cited README line (and the quoted context) and decide whether it is a genuine install/run/build/clone instruction **for that repository**.
3. Tick the box if it is correct. Leave it unticked and note the reason if it is an example for a sub-component, a template, or otherwise misleading.
4. Record the result at the bottom and file this document with the validation notes.

> Tip: `⚠ caution` marks commands whose nearby lines contain hedging words; check those first.

---
### deepset-ai/haystack

- Repo: <https://github.com/deepset-ai/haystack>
- Commands: 2

- [ ] `pip install haystack-ai` (high confidence, install, README L33)
  - L31: ``
  - L32: ````sh`
  - L33: `pip install haystack-ai`
  - L34: `````

- [ ] `pip install --pre haystack-ai` (high confidence, install, README L38)
  - L36: `Install nightly pre-releases to try the newest features:`
  - L37: ````sh`
  - L38: `pip install --pre haystack-ai`
  - L39: `````


### neuml/txtai

- Repo: <https://github.com/neuml/txtai>
- Commands: 1

- [ ] `pip install txtai` (high confidence, install, README L190)
  - L188: ``
  - L189: `````
  - L190: `pip install txtai`
  - L191: `````


### superduper-io/superduper

- Repo: <https://github.com/superduper-io/superduper>
- Commands: 5

- [ ] `pip install superduper-framework >= 0.7.0` (high confidence, install, README L43)
  - L41: ``
  - L42: ````bash`
  - L43: `pip install superduper-framework >= 0.7.0`
  - L44: `````

- [ ] `pip install superduper-mongodb >= 0.7.0` (high confidence, install, README L50)
  - L48: ````bash`
  - L49: `# at least one or more of the following:`
  - L50: `pip install superduper-mongodb >= 0.7.0`
  - L51: `# or`

- [ ] `pip install superduper-sql >= 0.7.0` (high confidence, install, README L52)
  - L50: `pip install superduper-mongodb >= 0.7.0`
  - L51: `# or`
  - L52: `pip install superduper-sql >= 0.7.0`
  - L53: `# or`

- [ ] `pip install superduper-snowflake >= 0.7.0` (high confidence, install, README L54)
  - L52: `pip install superduper-sql >= 0.7.0`
  - L53: `# or`
  - L54: `pip install superduper-snowflake >= 0.7.0`
  - L55: `# or`

- [ ] `pip install superduper-redis >= 0.7.0` (high confidence, install, README L56)
  - L54: `pip install superduper-snowflake >= 0.7.0`
  - L55: `# or`
  - L56: `pip install superduper-redis >= 0.7.0`
  - L57: `````


### langchain-ai/langchain

- Repo: <https://github.com/langchain-ai/langchain>
- Commands: 1

- [ ] `uv add langchain` (high confidence, install, README L32)
  - L30: ``
  - L31: ````bash`
  - L32: `uv add langchain`
  - L33: `````


### run-llama/llama_index

- Repo: <https://github.com/run-llama/llama_index>
- Commands: 4

- [ ] `pip install llama-index-core` (high confidence, install, README L115)
  - L113: ````sh`
  - L114: `# custom selection of integrations to work with core`
  - L115: `pip install llama-index-core`
  - L116: `pip install llama-index-llms-openai`

- [ ] `pip install llama-index-llms-openai` (high confidence, install, README L116)
  - L114: `# custom selection of integrations to work with core`
  - L115: `pip install llama-index-core`
  - L116: `pip install llama-index-llms-openai`
  - L117: `pip install llama-index-llms-ollama`

- [ ] `pip install llama-index-llms-ollama` (high confidence, install, README L117)
  - L115: `pip install llama-index-core`
  - L116: `pip install llama-index-llms-openai`
  - L117: `pip install llama-index-llms-ollama`
  - L118: `pip install llama-index-embeddings-huggingface`

- [ ] `pip install llama-index-embeddings-huggingface` (high confidence, install, README L118)
  - L116: `pip install llama-index-llms-openai`
  - L117: `pip install llama-index-llms-ollama`
  - L118: `pip install llama-index-embeddings-huggingface`
  - L119: `````


### langbot-app/LangBot

- Repo: <https://github.com/langbot-app/LangBot>
- Commands: 1

- [ ] `git clone https://github.com/langbot-app/LangBot` (medium confidence, clone, README L93)
  - L91: ``
  - L92: ````bash`
  - L93: `git clone https://github.com/langbot-app/LangBot`
  - L94: `cd LangBot/docker`


### Future-House/paper-qa

- Repo: <https://github.com/Future-House/paper-qa>
- Commands: 3

- [ ] `pip install paper-qa` (high confidence, install, README L77)
  - L75: ``
  - L76: ````bash`
  - L77: `pip install paper-qa`
  - L78: `mkdir my_papers`

- [ ] `pip install paper-qa>=5` (high confidence, install, README L251)
  - L249: ``
  - L250: ````bash`
  - L251: `pip install paper-qa>=5`
  - L252: `````

- [ ] `pip install paper-qa[local]` (medium confidence, install, README L726)
  - L724: ``
  - L725: ````sh`
  - L726: `pip install paper-qa[local]`
  - L727: `````


### chatchat-space/Langchain-Chatchat

- Repo: <https://github.com/chatchat-space/Langchain-Chatchat>
- Commands: 4

- [ ] `pip install langchain-chatchat -U` (medium confidence, install, README L141)
  - L139: ``
  - L140: ````shell`
  - L141: `pip install langchain-chatchat -U`
  - L142: `````

- [ ] `pip install "langchain-chatchat[xinference]" -U` (low confidence, install, README L151)
  - L149: `> 框架使用时，建议使用如下安装方式：`
  - L150: `> ```shell`
  - L151: `> pip install "langchain-chatchat[xinference]" -U`
  - L152: `> ````

- [ ] `docker pull chatimage/chatchat:0.3.1.3-93e2c87-20240829` (medium confidence, install, README L307)
  - L305: ``
  - L306: ````shell`
  - L307: `docker pull chatimage/chatchat:0.3.1.3-93e2c87-20240829`
  - L308: ``

- [ ] `docker pull ccr.ccs.tencentyun.com/langchain-chatchat/chatchat:0.3.1.3-93e2c87-20240829` (medium confidence, install, README L309)
  - L307: `docker pull chatimage/chatchat:0.3.1.3-93e2c87-20240829`
  - L308: ``
  - L309: `docker pull ccr.ccs.tencentyun.com/langchain-chatchat/chatchat:0.3.1.3-93e2c87-20240829 # 国内镜像`
  - L310: `````


### eosphoros-ai/DB-GPT

- Repo: <https://github.com/eosphoros-ai/DB-GPT>
- Commands: 1

- [ ] `pip install dbgpt-app` (medium confidence, install, README L202)
  - L200: ``
  - L201: ````bash`
  - L202: `pip install dbgpt-app`
  - L203: `dbgpt start`


### mem0ai/mem0

- Repo: <https://github.com/mem0ai/mem0>
- Commands: 5

- [ ] `npm install -g @mem0/cli` (medium confidence, install, README L96)
  - L94: ````bash`
  - L95: `# 1. Install`
  - L96: `npm install -g @mem0/cli      # or: pip install mem0-cli`
  - L97: ``

- [ ] `pip install mem0ai` (medium confidence, install, README L123)
  - L121: ``
  - L122: ````bash`
  - L123: `pip install mem0ai`
  - L124: `````

- [ ] `pip install mem0ai[nlp]` (medium confidence, install, README L129)
  - L127: ``
  - L128: ````bash`
  - L129: `pip install mem0ai[nlp]`
  - L130: `python -m spacy download en_core_web_sm`

- [ ] `npm install mem0ai` (medium confidence, install, README L136)
  - L134: ``
  - L135: ````bash`
  - L136: `npm install mem0ai`
  - L137: `````

- [ ] `npm install -g @mem0/cli` (medium confidence, install, README L164)
  - L162: ``
  - L163: ````bash`
  - L164: `npm install -g @mem0/cli   # or: pip install mem0-cli`
  - L165: ``


### pathwaycom/serviette

- Repo: <https://github.com/pathwaycom/serviette>
- Commands: 5

- [ ] `pip install serviette` (medium confidence, install, README L30)
  - L28: ``
  - L29: ````bash`
  - L30: `pip install serviette`
  - L31: `export PATHWAY_LICENSE_KEY=...        # free: https://pathway.com/framework/get-license`

- [ ] `pip install "serviette[local]" --extra-index-url https://download.pytorch.org/whl/cpu` (medium confidence, install, README L99)
  - L97: ``
  - L98: ````bash`
  - L99: `pip install "serviette[local]" --extra-index-url https://download.pytorch.org/whl/cpu`
  - L100: `# [local] = free local embeddings, the wizard's default. It brings PyTorch; the`

- [ ] `git clone https://github.com/pathwaycom/serviette.git && cd serviette` (medium confidence, clone, README L464)
  - L462: ``
  - L463: `# 1. serviette in its own virtualenv`
  - L464: `git clone https://github.com/pathwaycom/serviette.git && cd serviette`
  - L465: `python3.12 -m venv .venv`

- [ ] `pip install -e ".[dev,local]"` (medium confidence, install, README L467)
  - L465: `python3.12 -m venv .venv`
  - L466: `source .venv/bin/activate`
  - L467: `pip install -e ".[dev,local]"`
  - L468: ``

- [ ] `pip install "serviette[qdrant]"` (medium confidence, install, README L511)
  - L509: ``
  - L510: ````bash`
  - L511: `pip install "serviette[qdrant]"      # also: pgvector, milvus, chroma, weaviate,`
  - L512: `#       pinecone, mongodb, local, gemini, all`


### langchain-ai/langgraph

- Repo: <https://github.com/langchain-ai/langgraph>
- Commands: 1

- [ ] `pip install -U langgraph` (medium confidence, install, README L27)
  - L25: ``
  - L26: ````bash`
  - L27: `pip install -U langgraph`
  - L28: `````


### dataelement/bisheng

- Repo: <https://github.com/dataelement/bisheng>
- Commands: 1

- [ ] `git clone https://github.com/dataelement/bisheng.git` (medium confidence, clone, README L128)
  - L126: ``
  - L127: ````bash`
  - L128: `git clone https://github.com/dataelement/bisheng.git`
  - L129: `cd bisheng`


### 1Panel-dev/MaxKB

- Repo: <https://github.com/1Panel-dev/MaxKB>
- Commands: 1

- [ ] `docker run -d --name=maxkb --restart=always -p 8080:8080 -v ~/.maxkb:/opt/maxkb 1panel/maxkb` (high confidence, run, README L27)
  - L25: ``
  - L26: ````bash`
  - L27: `docker run -d --name=maxkb --restart=always -p 8080:8080 -v ~/.maxkb:/opt/maxkb 1panel/maxkb`
  - L28: `````


### TaskingAI/TaskingAI

- Repo: <https://github.com/TaskingAI/TaskingAI>
- Commands: 2

- [ ] `git clone https://github.com/taskingai/taskingai.git` (high confidence, clone, README L113)
  - L111: ``
  - L112: ````bash`
  - L113: `git clone https://github.com/taskingai/taskingai.git`
  - L114: `cd taskingai`

- [ ] `pip install taskingai` (medium confidence, install, README L172)
  - L170: ``
  - L171: ````bash`
  - L172: `pip install taskingai`
  - L173: `````


### ScrapeGraphAI/Scrapegraph-ai

- Repo: <https://github.com/ScrapeGraphAI/Scrapegraph-ai>
- Commands: 1

- [ ] `pip install scrapegraphai` (high confidence, install, README L59)
  - L57: ``
  - L58: ````bash`
  - L59: `pip install scrapegraphai`
  - L60: ``


### SciPhi-AI/R2R

- Repo: <https://github.com/SciPhi-AI/R2R>
- Commands: 3

- [ ] `pip install r2r` (high confidence, install, README L59)
  - L57: ````bash`
  - L58: `# Quick install and run in light mode`
  - L59: `pip install r2r`
  - L60: `export OPENAI_API_KEY=sk-...`

- [ ] `pip install r2r` (high confidence, install, README L80)
  - L78: ````bash`
  - L79: `# Install SDK`
  - L80: `pip install r2r  # Python`
  - L81: `# or`

- [ ] `npm i r2r-js` (high confidence, install, README L82)
  - L80: `pip install r2r  # Python`
  - L81: `# or`
  - L82: `npm i r2r-js    # JavaScript`
  - L83: `````


### lavague-ai/LaVague

- Repo: <https://github.com/lavague-ai/LaVague>
- Commands: 1

- [ ] `pip install lavague` (medium confidence, install, README L62)
  - L60: ``
  - L61: ````bash`
  - L62: `pip install lavague`
  - L63: `````


### Canner/WrenAI

- Repo: <https://github.com/Canner/WrenAI>
- Commands: 2

- [ ] `pip install wrenai` (high confidence, install, README L50)
  - L48: ``
  - L49: ````bash`
  - L50: `pip install wrenai`
  - L51: `````

- [ ] `pip install wrenai -i https://pypi.tuna.tsinghua.edu.cn/simple` (high confidence, install, README L75)
  - L73: ``
  - L74: ````bash`
  - L75: `pip install wrenai -i https://pypi.tuna.tsinghua.edu.cn/simple`
  - L76: `````


### Cinnamon/kotaemon

- Repo: <https://github.com/Cinnamon/kotaemon>
- Commands: 7

- [ ] `docker run -e GRADIO_SERVER_NAME=0.0.0.0 -e GRADIO_SERVER_PORT=7860 -v ./ktem_app_data:/app/ktem_app_data -p 7860:7860 -it --rm ghcr.io/cinnamon/kotaemon:main-full` (medium confidence, run, README L104)
  - L102: ``
  - L103: ````shell`
  - L104: `docker run \`
  - L105: `-e GRADIO_SERVER_NAME=0.0.0.0 \`

- [ ] `docker run -e GRADIO_SERVER_NAME=0.0.0.0 -e GRADIO_SERVER_PORT=7860 -v ./ktem_app_data:/app/ktem_app_data -p 7860:7860 -it --rm --platform linux/arm64 ghcr.io/cinnamon/kotaemon:main-lite` (medium confidence, run, README L130)
  - L128: ````shell`
  - L129: `# To run docker with platform linux/arm64`
  - L130: `docker run \`
  - L131: `-e GRADIO_SERVER_NAME=0.0.0.0 \`

- [ ] `git clone https://github.com/Cinnamon/kotaemon` (medium confidence, clone, README L148)
  - L146: ``
  - L147: ````shell`
  - L148: `git clone https://github.com/Cinnamon/kotaemon`
  - L149: `cd kotaemon`

- [ ] `conda create -n kotaemon python=3.10` (medium confidence, install, README L164)
  - L162: ``
  - L163: ````shell`
  - L164: `conda create -n kotaemon python=3.10`
  - L165: `conda activate kotaemon`

- [ ] `pip install -e "libs/kotaemon[all]"` (medium confidence, install, README L167)
  - L165: `conda activate kotaemon`
  - L166: ``
  - L167: `pip install -e "libs/kotaemon[all]"`
  - L168: `pip install -e "libs/ktem"`

- [ ] `pip install -e "libs/ktem"` (medium confidence, install, README L168)
  - L166: ``
  - L167: `pip install -e "libs/kotaemon[all]"`
  - L168: `pip install -e "libs/ktem"`
  - L169: `````

- [ ] `pip install "graphrag<=0.3.6" future` (high confidence, install, README L229)
  - L227: ``
  - L228: ````shell`
  - L229: `pip install "graphrag<=0.3.6" future`
  - L230: `````


### PacktPublishing/LLM-Engineers-Handbook

- Repo: <https://github.com/PacktPublishing/LLM-Engineers-Handbook>
- Commands: 1

- [ ] `git clone https://github.com/PacktPublishing/LLM-Engineers-Handbook.git` (medium confidence, clone, README L126)
  - L124: ``
  - L125: ````bash`
  - L126: `git clone https://github.com/PacktPublishing/LLM-Engineers-Handbook.git`
  - L127: `cd LLM-Engineers-Handbook`


### Shubhamsaboo/awesome-llm-apps

- Repo: <https://github.com/Shubhamsaboo/awesome-llm-apps>
- Commands: 2

- [ ] `git clone https://github.com/Shubhamsaboo/awesome-llm-apps.git` (high confidence, clone, README L66)
  - L64: ``
  - L65: ````bash`
  - L66: `git clone https://github.com/Shubhamsaboo/awesome-llm-apps.git`
  - L67: `cd awesome-llm-apps/starter_ai_agents/ai_travel_agent`

- [ ] `pip install -r requirements.txt` (high confidence, install, README L68)
  - L66: `git clone https://github.com/Shubhamsaboo/awesome-llm-apps.git`
  - L67: `cd awesome-llm-apps/starter_ai_agents/ai_travel_agent`
  - L68: `pip install -r requirements.txt`
  - L69: `streamlit run travel_agent.py`


### unclecode/crawl4ai

- Repo: <https://github.com/unclecode/crawl4ai>
- Commands: 5

- [ ] `pip install -U crawl4ai` (high confidence, install, README L122)
  - L120: ``
  - L121: ````bash`
  - L122: `pip install -U crawl4ai`
  - L123: `crawl4ai-setup        # installs the browser, once`

- [ ] `pip install -U crawl4ai` (high confidence, install, README L256)
  - L254: ``
  - L255: ````bash`
  - L256: `pip install -U crawl4ai`
  - L257: `crawl4ai-setup      # installs and sets up the browser`

- [ ] `git clone https://github.com/unclecode/crawl4ai.git` (high confidence, clone, README L272)
  - L270: ``
  - L271: ````bash`
  - L272: `git clone https://github.com/unclecode/crawl4ai.git`
  - L273: `cd crawl4ai`

- [ ] `pip install -e ".[all]"` (high confidence, install, README L274)
  - L272: `git clone https://github.com/unclecode/crawl4ai.git`
  - L273: `cd crawl4ai`
  - L274: `pip install -e ".[all]"     # or: pip install -e .   (the core only)`
  - L275: `````

- [ ] `docker run -d -p 11235:11235 --name crawl4ai --shm-size=1g -e CRAWL4AI_API_TOKEN="$CRAWL4AI_API_TOKEN" unclecode/crawl4ai:latest` (high confidence, run, README L285)
  - L283: ````bash`
  - L284: `export CRAWL4AI_API_TOKEN="$(openssl rand -hex 32)"`
  - L285: `docker run -d -p 11235:11235 --name crawl4ai --shm-size=1g \`
  - L286: `-e CRAWL4AI_API_TOKEN="$CRAWL4AI_API_TOKEN" \`


### xerrors/Yuxi

- Repo: <https://github.com/xerrors/Yuxi>
- Commands: 1

- [ ] `git clone --branch v0.8.0 --depth 1 https://github.com/xerrors/Yuxi.git` (medium confidence, clone, README L39)
  - L37: ``
  - L38: ````bash`
  - L39: `git clone --branch v0.8.0 --depth 1 https://github.com/xerrors/Yuxi.git`
  - L40: `cd Yuxi`


### getzep/graphiti

- Repo: <https://github.com/getzep/graphiti>
- Commands: 20

- [ ] `docker run -p 6379:6379 -p 3000:3000 -it --rm falkordb/falkordb:latest` (medium confidence, run, README L183) **⚠ caution**
  - L181: `> Alternatively, you can use FalkorDB on-premises via Docker and instantly start with the quickstart example:`
  - L182: `> ````
  - L183: `> docker run -p 6379:6379 -p 3000:3000 -it --rm falkordb/falkordb:latest`
  - L184: `> ````

- [ ] `pip install graphiti-core` (high confidence, install, README L187)
  - L185: ``
  - L186: ````bash`
  - L187: `pip install graphiti-core`
  - L188: `````

- [ ] `uv add graphiti-core` (high confidence, install, README L193)
  - L191: ``
  - L192: ````bash`
  - L193: `uv add graphiti-core`
  - L194: `````

- [ ] `pip install graphiti-core[falkordb]` (high confidence, install, README L201)
  - L199: ``
  - L200: ````bash`
  - L201: `pip install graphiti-core[falkordb]`
  - L202: ``

- [ ] `uv add graphiti-core[falkordb]` (high confidence, install, README L204)
  - L202: ``
  - L203: `# or with uv`
  - L204: `uv add graphiti-core[falkordb]`
  - L205: ``

- [ ] `pip install graphiti-core[falkordblite]` (high confidence, install, README L207)
  - L205: ``
  - L206: `# or embedded version (requires Python 3.12+)`
  - L207: `pip install graphiti-core[falkordblite]`
  - L208: `# or with uv`

- [ ] `uv add graphiti-core[falkordblite]` (high confidence, install, README L209)
  - L207: `pip install graphiti-core[falkordblite]`
  - L208: `# or with uv`
  - L209: `uv add graphiti-core[falkordblite]`
  - L210: `````

- [ ] `pip install graphiti-core[neptune]` (high confidence, install, README L217)
  - L215: ``
  - L216: ````bash`
  - L217: `pip install graphiti-core[neptune]`
  - L218: ``

- [ ] `uv add graphiti-core[neptune]` (high confidence, install, README L220)
  - L218: ``
  - L219: `# or with uv`
  - L220: `uv add graphiti-core[neptune]`
  - L221: `````

- [ ] `pip install graphiti-core[relate]` (high confidence, install, README L229)
  - L227: ``
  - L228: ````bash`
  - L229: `pip install graphiti-core[relate]`
  - L230: ``

- [ ] `uv add graphiti-core[relate]` (high confidence, install, README L232)
  - L230: ``
  - L231: `# or with uv`
  - L232: `uv add graphiti-core[relate]`
  - L233: `````

- [ ] `pip install graphiti-core[anthropic]` (high confidence, install, README L248)
  - L246: ````bash`
  - L247: `# Install with Anthropic support`
  - L248: `pip install graphiti-core[anthropic]`
  - L249: ``

- [ ] `pip install graphiti-core[groq]` (high confidence, install, README L251)
  - L249: ``
  - L250: `# Install with Groq support`
  - L251: `pip install graphiti-core[groq]`
  - L252: ``

- [ ] `pip install graphiti-core[google-genai]` (high confidence, install, README L254)
  - L252: ``
  - L253: `# Install with Google Gemini support`
  - L254: `pip install graphiti-core[google-genai]`
  - L255: ``

- [ ] `pip install graphiti-core[anthropic,groq,google-genai]` (high confidence, install, README L257)
  - L255: ``
  - L256: `# Install with multiple providers`
  - L257: `pip install graphiti-core[anthropic,groq,google-genai]`
  - L258: ``

- [ ] `pip install graphiti-core[falkordb,anthropic,google-genai]` (high confidence, install, README L260)
  - L258: ``
  - L259: `# Install with FalkorDB and LLM providers`
  - L260: `pip install graphiti-core[falkordb,anthropic,google-genai]`
  - L261: ``

- [ ] `pip install graphiti-core[neptune]` (high confidence, install, README L263)
  - L261: ``
  - L262: `# Install with Amazon Neptune`
  - L263: `pip install graphiti-core[neptune]`
  - L264: `````

- [ ] `docker compose up` (high confidence, run, README L308)
  - L306: ``
  - L307: ````bash`
  - L308: `docker compose up`
  - L309: `````

- [ ] `uv add "graphiti-core[google-genai]"` (medium confidence, install, README L509)
  - L507: ``
  - L508: ````bash`
  - L509: `uv add "graphiti-core[google-genai]"`
  - L510: ``

- [ ] `pip install "graphiti-core[google-genai]"` (medium confidence, install, README L513)
  - L511: `# or`
  - L512: ``
  - L513: `pip install "graphiti-core[google-genai]"`
  - L514: `````


### potpie-ai/potpie

- Repo: <https://github.com/potpie-ai/potpie>
- Commands: 1

- [ ] `python3 -m pip install --user potpie` (high confidence, install, README L31)
  - L29: ``
  - L30: ````bash`
  - L31: `python3 -m pip install --user potpie`
  - L32: `````


### HKUDS/LightRAG

- Repo: <https://github.com/HKUDS/LightRAG>
- Commands: 5

- [ ] `git clone https://github.com/HKUDS/LightRAG.git` (high confidence, clone, README L144)
  - L142: ``
  - L143: ````bash`
  - L144: `git clone https://github.com/HKUDS/LightRAG.git`
  - L145: `cd LightRAG`

- [ ] `bun install --frozen-lockfile` (high confidence, install, README L167)
  - L165: ````bash`
  - L166: `cd lightrag_webui`
  - L167: `bun install --frozen-lockfile`
  - L168: `bun run build`

- [ ] `git clone https://github.com/HKUDS/LightRAG.git` (medium confidence, clone, README L204)
  - L202: ``
  - L203: ````bash`
  - L204: `git clone https://github.com/HKUDS/LightRAG.git`
  - L205: `cd LightRAG`

- [ ] `docker compose up` (medium confidence, run, README L207)
  - L205: `cd LightRAG`
  - L206: `cp env.example .env  # edit it first: see "Minimum .env Changes" below`
  - L207: `docker compose up`
  - L208: `````

- [ ] `brew install cairo` (medium confidence, install, README L281)
  - L279: ``
  - L280: `# macOS (Homebrew)`
  - L281: `brew install cairo`
  - L282: ``


### OpenBMB/UltraRAG

- Repo: <https://github.com/OpenBMB/UltraRAG>
- Commands: 10

- [ ] `python -m pip install --upgrade "pip>=26.2.2" "uv==0.13.7"` (high confidence, install, README L130)
  - L128: ````shell`
  - L129: `## Direct installation`
  - L130: `python -m pip install --upgrade "pip>=26.2.2" "uv==0.13.7"`
  - L131: `## Download`

- [ ] `git clone https://github.com/OpenBMB/UltraRAG.git --depth 1` (high confidence, clone, README L138)
  - L136: ``
  - L137: ````shell`
  - L138: `git clone https://github.com/OpenBMB/UltraRAG.git --depth 1`
  - L139: `cd UltraRAG`

- [ ] `git clone https://github.com/OpenBMB/UltraRAG.git --depth 1` (medium confidence, clone, README L213)
  - L211: ````shell`
  - L212: `# 1. Clone the repository`
  - L213: `git clone https://github.com/OpenBMB/UltraRAG.git --depth 1`
  - L214: `cd UltraRAG`

- [ ] `docker pull hdxin2002/ultrarag:latest-base-cpu` (medium confidence, install, README L218)
  - L216: `# 2. Prepare the image (choose one)`
  - L217: `# Option A: Pull from Docker Hub`
  - L218: `docker pull hdxin2002/ultrarag:latest-base-cpu # Core dependencies (CPU)`
  - L219: `docker pull hdxin2002/ultrarag:latest-base-gpu # Core dependencies (GPU base)`

- [ ] `docker pull hdxin2002/ultrarag:latest-base-gpu` (medium confidence, install, README L219)
  - L217: `# Option A: Pull from Docker Hub`
  - L218: `docker pull hdxin2002/ultrarag:latest-base-cpu # Core dependencies (CPU)`
  - L219: `docker pull hdxin2002/ultrarag:latest-base-gpu # Core dependencies (GPU base)`
  - L220: `docker pull hdxin2002/ultrarag:latest          # All extras (GPU)`

- [ ] `docker pull hdxin2002/ultrarag:latest` (medium confidence, install, README L220)
  - L218: `docker pull hdxin2002/ultrarag:latest-base-cpu # Core dependencies (CPU)`
  - L219: `docker pull hdxin2002/ultrarag:latest-base-gpu # Core dependencies (GPU base)`
  - L220: `docker pull hdxin2002/ultrarag:latest          # All extras (GPU)`
  - L221: ``

- [ ] `docker build -f Dockerfile.base-cpu -t ultrarag:latest-base-cpu .` (medium confidence, build, README L223)
  - L221: ``
  - L222: `# Option B: Build locally`
  - L223: `docker build -f Dockerfile.base-cpu -t ultrarag:latest-base-cpu . # CPU`
  - L224: `docker build -t ultrarag:latest .                              # Full GPU image`

- [ ] `docker build -t ultrarag:latest .` (medium confidence, build, README L224)
  - L222: `# Option B: Build locally`
  - L223: `docker build -f Dockerfile.base-cpu -t ultrarag:latest-base-cpu . # CPU`
  - L224: `docker build -t ultrarag:latest .                              # Full GPU image`
  - L225: `````

- [ ] `docker run --rm -it -p 5050:5050 hdxin2002/ultrarag:latest-base-cpu` (medium confidence, run, README L242)
  - L240: ````shell`
  - L241: `# CPU: no GPU runtime required`
  - L242: `docker run --rm -it -p 5050:5050 hdxin2002/ultrarag:latest-base-cpu`
  - L243: ``

- [ ] `docker run --rm -it --gpus all -p 5050:5050 hdxin2002/ultrarag:latest` (medium confidence, run, README L245)
  - L243: ``
  - L244: `# GPU: requires the NVIDIA Container Toolkit`
  - L245: `docker run --rm -it --gpus all -p 5050:5050 hdxin2002/ultrarag:latest`
  - L246: `````


### zilliztech/deep-searcher

- Repo: <https://github.com/zilliztech/deep-searcher>
- Commands: 4

- [ ] `pip install deepsearcher` (medium confidence, install, README L45)
  - L43: `Install DeepSearcher`
  - L44: ````bash`
  - L45: `pip install deepsearcher`
  - L46: `````

- [ ] `pip install "deepsearcher[ollama]"` (medium confidence, install, README L50) **⚠ caution**
  - L48: `For optional dependencies, e.g., ollama:`
  - L49: ````bash`
  - L50: `pip install "deepsearcher[ollama]"`
  - L51: `````

- [ ] `git clone https://github.com/zilliztech/deep-searcher.git && cd deep-searcher` (high confidence, clone, README L58)
  - L56: `Clone the repository and navigate to the project directory:`
  - L57: ````shell`
  - L58: `git clone https://github.com/zilliztech/deep-searcher.git && cd deep-searcher`
  - L59: `````

- [ ] `pip install nest_asyncio` (medium confidence, install, README L543)
  - L541: ``
  - L542: `````
  - L543: `pip install nest_asyncio`
  - L544: `````


### VectifyAI/PageIndex

- Repo: <https://github.com/VectifyAI/PageIndex>
- Commands: 2

- [ ] `pip install -U pageindex` (high confidence, install, README L84)
  - L82: ``
  - L83: ````bash`
  - L84: `pip install -U pageindex`
  - L85: `````

- [ ] `pip install -U pageindex` (high confidence, install, README L185)
  - L183: ``
  - L184: ````bash`
  - L185: `pip install -U pageindex`
  - L186: `````


### ModelEngine-Group/nexent

- Repo: <https://github.com/ModelEngine-Group/nexent>
- Commands: 2

- [ ] `git clone https://github.com/ModelEngine-Group/nexent.git` (medium confidence, clone, README L44)
  - L42: ``
  - L43: ````bash`
  - L44: `git clone https://github.com/ModelEngine-Group/nexent.git`
  - L45: `cd nexent`

- [ ] `git clone https://github.com/ModelEngine-Group/nexent.git` (medium confidence, clone, README L64)
  - L62: ``
  - L63: ````bash`
  - L64: `git clone https://github.com/ModelEngine-Group/nexent.git`
  - L65: `cd nexent`


### StarTrail-org/LEANN

- Repo: <https://github.com/StarTrail-org/LEANN>
- Commands: 7

- [ ] `git clone https://github.com/StarTrail-org/LEANN.git leann` (high confidence, clone, README L107)
  - L105: ``
  - L106: ````bash`
  - L107: `git clone https://github.com/StarTrail-org/LEANN.git leann`
  - L108: `cd leann`

- [ ] `git clone https://github.com/StarTrail-org/LEANN.git leann` (high confidence, clone, README L136)
  - L134: ``
  - L135: ````bash`
  - L136: `git clone https://github.com/StarTrail-org/LEANN.git leann`
  - L137: `cd leann`

- [ ] `brew install libomp boost protobuf zeromq pkgconf` (high confidence, install, README L146)
  - L144: ``
  - L145: ````bash`
  - L146: `brew install libomp boost protobuf zeromq pkgconf`
  - L147: `uv sync --extra diskann`

- [ ] `git clone https://aur.archlinux.org/paru-bin.git` (high confidence, clone, README L173)
  - L171: `# For MKL in DiskANN`
  - L172: `sudo pacman -S --needed base-devel git`
  - L173: `git clone https://aur.archlinux.org/paru-bin.git`
  - L174: `cd paru-bin && makepkg -si`

- [ ] `pip install "mineru>=4.0,<5"` (medium confidence, install, README L470)
  - L468: ``
  - L469: ````bash`
  - L470: `pip install "mineru>=4.0,<5"`
  - L471: ``

- [ ] `brew install poppler` (medium confidence, install, README L513)
  - L511: `# Install dependencies`
  - L512: `uv pip install colpali_engine pdf2image pillow matplotlib qwen_vl_utils einops seaborn`
  - L513: `brew install poppler  # macOS only, for PDF processing`
  - L514: `````

- [ ] `brew install sunnyyoung/repo/wechattweak-cli` (medium confidence, install, README L658)
  - L656: ``
  - L657: ````bash`
  - L658: `brew install sunnyyoung/repo/wechattweak-cli`
  - L659: `````


### volcengine/MineContext

- Repo: <https://github.com/volcengine/MineContext>
- Commands: 3

- [ ] `pnpm install` (high confidence, install, README L251)
  - L249: `pip config unset global.index-url`
  - L250: `cd frontend`
  - L251: `pnpm install`
  - L252: `````

- [ ] `git clone https://github.com/volcengine/MineContext.git` (high confidence, clone, README L341)
  - L339: ````bash`
  - L340: `# Clone repository`
  - L341: `git clone https://github.com/volcengine/MineContext.git`
  - L342: `cd MineContext`

- [ ] `pip install -e .` (high confidence, install, README L407)
  - L405: ````bash`
  - L406: `source .venv/bin/activate  # On Windows: .venv\Scripts\activate`
  - L407: `pip install -e .`
  - L408: `opencontext start --port 1733`


### MemoriLabs/Memori

- Repo: <https://github.com/MemoriLabs/Memori>
- Commands: 3

- [ ] `npm install @memorilabs/memori` (high confidence, install, README L44)
  - L42: ``
  - L43: ````bash`
  - L44: `npm install @memorilabs/memori`
  - L45: `````

- [ ] `pip install memori` (high confidence, install, README L52)
  - L50: ``
  - L51: ````bash`
  - L52: `pip install memori`
  - L53: `````

- [ ] `pip install hermes-memori` (medium confidence, install, README L163)
  - L161: ``
  - L162: ````bash`
  - L163: `pip install hermes-memori`
  - L164: `hermes-memori install`


### bojieli/ai-agent-book

- Repo: <https://github.com/bojieli/ai-agent-book>
- Commands: 25

- [ ] `git clone https://github.com/bojieli/ai-agent-book.git` (medium confidence, clone, README L89)
  - L87: ``
  - L88: ````bash`
  - L89: `git clone https://github.com/bojieli/ai-agent-book.git`
  - L90: `cd ai-agent-book`

- [ ] `python -m pip install -e ".[ch1]"` (medium confidence, install, README L102)
  - L100: ``
  - L101: `# 未安装 uv 时：使用 pip 从 pyproject.toml 重新解析`
  - L102: `python -m pip install -e ".[ch1]"`
  - L103: `````

- [ ] `git clone https://github.com/anthropics/claude-quickstarts.git chapter6/claude-quickstarts && git -C chapter6/claude-quickstarts checkout --detach 9bcc95e316e5ef6542b4c9d0469f4078829eead5` (medium confidence, clone, README L187)
  - L185: ````bash`
  - L186: `# 第 6 章 · GUI 与机器人外部复现轨道`
  - L187: `git clone https://github.com/anthropics/claude-quickstarts.git chapter6/claude-quickstarts && git -C chapter6/claude-quickstarts checkout --detach 9bcc95e316e5ef6542b4c9d0469f4078829eead5  # 实验 6-9 使用`
  - L188: `git clone https://github.com/browser-use/browser-use.git chapter6/browser-use && git -C chapter6/browser-use checkout --detach ec9277c5001f2cb78ee419c927775a3cfc227ff8  # 实验 6-10`

- [ ] `git clone https://github.com/browser-use/browser-use.git chapter6/browser-use && git -C chapter6/browser-use checkout --detach ec9277c5001f2cb78ee419c927775a3cfc227ff8` (medium confidence, clone, README L188)
  - L186: `# 第 6 章 · GUI 与机器人外部复现轨道`
  - L187: `git clone https://github.com/anthropics/claude-quickstarts.git chapter6/claude-quickstarts && git -C chapter6/claude-quickstarts checkout --detach 9bcc95e316e5ef6542b4c9d0469f4078829eead5  # 实验 6-9 使用`
  - L188: `git clone https://github.com/browser-use/browser-use.git chapter6/browser-use && git -C chapter6/browser-use checkout --detach ec9277c5001f2cb78ee419c927775a3cfc227ff8  # 实验 6-10`
  - L189: `git clone https://github.com/Vector-Wangel/XLeRobot.git chapter6/XLeRobot && git -C chapter6/XLeRobot fetch origin 3d14695e40c9c68229c0aacffca6053c75cd3eb6 && git -C chapter6/XLeRobot checkout --detac`

- [ ] `git clone https://github.com/Vector-Wangel/XLeRobot.git chapter6/XLeRobot && git -C chapter6/XLeRobot fetch origin 3d14695e40c9c68229c0aacffca6053c75cd3eb6 && git -C chapter6/XLeRobot checkout --detach 3d14695e40c9c68229c0aacffca6053c75cd3eb6 && test "$(git -C chapter6/XLeRobot rev-parse HEAD)" = "3d14695e40c9c68229c0aacffca6053c75cd3eb6"` (medium confidence, clone, README L189)
  - L187: `git clone https://github.com/anthropics/claude-quickstarts.git chapter6/claude-quickstarts && git -C chapter6/claude-quickstarts checkout --detach 9bcc95e316e5ef6542b4c9d0469f4078829eead5  # 实验 6-9 使用`
  - L188: `git clone https://github.com/browser-use/browser-use.git chapter6/browser-use && git -C chapter6/browser-use checkout --detach ec9277c5001f2cb78ee419c927775a3cfc227ff8  # 实验 6-10`
  - L189: `git clone https://github.com/Vector-Wangel/XLeRobot.git chapter6/XLeRobot && git -C chapter6/XLeRobot fetch origin 3d14695e40c9c68229c0aacffca6053c75cd3eb6 && git -C chapter6/XLeRobot checkout --detac`
  - L190: `git clone https://github.com/Grigorij-Dudnik/RoboCrew.git chapter6/RoboCrew && git -C chapter6/RoboCrew fetch origin c749148f29bd14e61347f9fc3530c343fff0d994 && git -C chapter6/RoboCrew checkout --det`

- [ ] `git clone https://github.com/Grigorij-Dudnik/RoboCrew.git chapter6/RoboCrew && git -C chapter6/RoboCrew fetch origin c749148f29bd14e61347f9fc3530c343fff0d994 && git -C chapter6/RoboCrew checkout --detach c749148f29bd14e61347f9fc3530c343fff0d994 && test "$(git -C chapter6/RoboCrew rev-parse HEAD)" = "c749148f29bd14e61347f9fc3530c343fff0d994"` (medium confidence, clone, README L190)
  - L188: `git clone https://github.com/browser-use/browser-use.git chapter6/browser-use && git -C chapter6/browser-use checkout --detach ec9277c5001f2cb78ee419c927775a3cfc227ff8  # 实验 6-10`
  - L189: `git clone https://github.com/Vector-Wangel/XLeRobot.git chapter6/XLeRobot && git -C chapter6/XLeRobot fetch origin 3d14695e40c9c68229c0aacffca6053c75cd3eb6 && git -C chapter6/XLeRobot checkout --detac`
  - L190: `git clone https://github.com/Grigorij-Dudnik/RoboCrew.git chapter6/RoboCrew && git -C chapter6/RoboCrew fetch origin c749148f29bd14e61347f9fc3530c343fff0d994 && git -C chapter6/RoboCrew checkout --det`
  - L191: `git clone https://github.com/StoneT2000/lerobot-sim2real.git chapter6/lerobot-sim2real && git -C chapter6/lerobot-sim2real fetch origin 87d6c1d969f6e0ca4dc5697940804e231118a63a && git -C chapter6/lero`

- [ ] `git clone https://github.com/StoneT2000/lerobot-sim2real.git chapter6/lerobot-sim2real && git -C chapter6/lerobot-sim2real fetch origin 87d6c1d969f6e0ca4dc5697940804e231118a63a && git -C chapter6/lerobot-sim2real checkout --detach 87d6c1d969f6e0ca4dc5697940804e231118a63a && test "$(git -C chapter6/lerobot-sim2real rev-parse HEAD)" = "87d6c1d969f6e0ca4dc5697940804e231118a63a"` (medium confidence, clone, README L191)
  - L189: `git clone https://github.com/Vector-Wangel/XLeRobot.git chapter6/XLeRobot && git -C chapter6/XLeRobot fetch origin 3d14695e40c9c68229c0aacffca6053c75cd3eb6 && git -C chapter6/XLeRobot checkout --detac`
  - L190: `git clone https://github.com/Grigorij-Dudnik/RoboCrew.git chapter6/RoboCrew && git -C chapter6/RoboCrew fetch origin c749148f29bd14e61347f9fc3530c343fff0d994 && git -C chapter6/RoboCrew checkout --det`
  - L191: `git clone https://github.com/StoneT2000/lerobot-sim2real.git chapter6/lerobot-sim2real && git -C chapter6/lerobot-sim2real fetch origin 87d6c1d969f6e0ca4dc5697940804e231118a63a && git -C chapter6/lero`
  - L192: ``

- [ ] `git clone https://github.com/google-research/android_world.git chapter7/android_world && git -C chapter7/android_world checkout --detach 0e95d641e244504c22087cc29b013f3b2428a261` (medium confidence, clone, README L194)
  - L192: ``
  - L193: `# 第 7 章 · 评测基准`
  - L194: `git clone https://github.com/google-research/android_world.git chapter7/android_world && git -C chapter7/android_world checkout --detach 0e95d641e244504c22087cc29b013f3b2428a261`
  - L195: `git clone https://huggingface.co/datasets/gaia-benchmark/GAIA chapter7/GAIA && git -C chapter7/GAIA checkout --detach 682dd723ee1e1697e00360edccf2366dc8418dd9`

- [ ] `git clone https://huggingface.co/datasets/gaia-benchmark/GAIA chapter7/GAIA && git -C chapter7/GAIA checkout --detach 682dd723ee1e1697e00360edccf2366dc8418dd9` (medium confidence, clone, README L195)
  - L193: `# 第 7 章 · 评测基准`
  - L194: `git clone https://github.com/google-research/android_world.git chapter7/android_world && git -C chapter7/android_world checkout --detach 0e95d641e244504c22087cc29b013f3b2428a261`
  - L195: `git clone https://huggingface.co/datasets/gaia-benchmark/GAIA chapter7/GAIA && git -C chapter7/GAIA checkout --detach 682dd723ee1e1697e00360edccf2366dc8418dd9`
  - L196: `git clone https://github.com/xlang-ai/OSWorld.git chapter7/OSWorld && git -C chapter7/OSWorld checkout --detach 8365edc975efd0477a0d62444a5beed562ab5a7b`

- [ ] `git clone https://github.com/xlang-ai/OSWorld.git chapter7/OSWorld && git -C chapter7/OSWorld checkout --detach 8365edc975efd0477a0d62444a5beed562ab5a7b` (medium confidence, clone, README L196)
  - L194: `git clone https://github.com/google-research/android_world.git chapter7/android_world && git -C chapter7/android_world checkout --detach 0e95d641e244504c22087cc29b013f3b2428a261`
  - L195: `git clone https://huggingface.co/datasets/gaia-benchmark/GAIA chapter7/GAIA && git -C chapter7/GAIA checkout --detach 682dd723ee1e1697e00360edccf2366dc8418dd9`
  - L196: `git clone https://github.com/xlang-ai/OSWorld.git chapter7/OSWorld && git -C chapter7/OSWorld checkout --detach 8365edc975efd0477a0d62444a5beed562ab5a7b`
  - L197: `git clone https://github.com/SWE-bench/SWE-bench.git chapter7/SWE-bench && git -C chapter7/SWE-bench checkout --detach 5cd4be9fb23971679cbbafe5a0ecade27cef99be`

- [ ] `git clone https://github.com/SWE-bench/SWE-bench.git chapter7/SWE-bench && git -C chapter7/SWE-bench checkout --detach 5cd4be9fb23971679cbbafe5a0ecade27cef99be` (medium confidence, clone, README L197)
  - L195: `git clone https://huggingface.co/datasets/gaia-benchmark/GAIA chapter7/GAIA && git -C chapter7/GAIA checkout --detach 682dd723ee1e1697e00360edccf2366dc8418dd9`
  - L196: `git clone https://github.com/xlang-ai/OSWorld.git chapter7/OSWorld && git -C chapter7/OSWorld checkout --detach 8365edc975efd0477a0d62444a5beed562ab5a7b`
  - L197: `git clone https://github.com/SWE-bench/SWE-bench.git chapter7/SWE-bench && git -C chapter7/SWE-bench checkout --detach 5cd4be9fb23971679cbbafe5a0ecade27cef99be`
  - L198: `git clone https://github.com/sierra-research/tau2-bench.git chapter7/tau2-bench && git -C chapter7/tau2-bench checkout --detach 8d005b0e5b9e4af0bc055886fa7f95fc86d1710e`

- [ ] `git clone https://github.com/sierra-research/tau2-bench.git chapter7/tau2-bench && git -C chapter7/tau2-bench checkout --detach 8d005b0e5b9e4af0bc055886fa7f95fc86d1710e` (medium confidence, clone, README L198)
  - L196: `git clone https://github.com/xlang-ai/OSWorld.git chapter7/OSWorld && git -C chapter7/OSWorld checkout --detach 8365edc975efd0477a0d62444a5beed562ab5a7b`
  - L197: `git clone https://github.com/SWE-bench/SWE-bench.git chapter7/SWE-bench && git -C chapter7/SWE-bench checkout --detach 5cd4be9fb23971679cbbafe5a0ecade27cef99be`
  - L198: `git clone https://github.com/sierra-research/tau2-bench.git chapter7/tau2-bench && git -C chapter7/tau2-bench checkout --detach 8d005b0e5b9e4af0bc055886fa7f95fc86d1710e`
  - L199: `git clone https://github.com/laude-institute/terminal-bench.git chapter7/terminal-bench && git -C chapter7/terminal-bench checkout --detach 8384a179b1b8688f6ea5233a4d9d51218df1ac96`

- [ ] `git clone https://github.com/laude-institute/terminal-bench.git chapter7/terminal-bench && git -C chapter7/terminal-bench checkout --detach 8384a179b1b8688f6ea5233a4d9d51218df1ac96` (medium confidence, clone, README L199)
  - L197: `git clone https://github.com/SWE-bench/SWE-bench.git chapter7/SWE-bench && git -C chapter7/SWE-bench checkout --detach 5cd4be9fb23971679cbbafe5a0ecade27cef99be`
  - L198: `git clone https://github.com/sierra-research/tau2-bench.git chapter7/tau2-bench && git -C chapter7/tau2-bench checkout --detach 8d005b0e5b9e4af0bc055886fa7f95fc86d1710e`
  - L199: `git clone https://github.com/laude-institute/terminal-bench.git chapter7/terminal-bench && git -C chapter7/terminal-bench checkout --detach 8384a179b1b8688f6ea5233a4d9d51218df1ac96`
  - L200: ``

- [ ] `git clone https://github.com/bojieli/minimind.git chapter8/MiniMind-pretrain/minimind && git -C chapter8/MiniMind-pretrain/minimind fetch origin 8bdc5d97d5845a8c1ac2ed56a5b8b4c0d0fb0795 && git -C chapter8/MiniMind-pretrain/minimind checkout --detach 8bdc5d97d5845a8c1ac2ed56a5b8b4c0d0fb0795 && test "$(git -C chapter8/MiniMind-pretrain/minimind rev-parse HEAD)" = "8bdc5d97d5845a8c1ac2ed56a5b8b4c0d0fb0795"` (medium confidence, clone, README L202)
  - L200: ``
  - L201: `# 第 8 章 · 训练框架（bojieli/* 为本书适配的分支）`
  - L202: `git clone https://github.com/bojieli/minimind.git chapter8/MiniMind-pretrain/minimind && git -C chapter8/MiniMind-pretrain/minimind fetch origin 8bdc5d97d5845a8c1ac2ed56a5b8b4c0d0fb0795 && git -C chap`
  - L203: `git clone https://github.com/bojieli/minimind-v.git chapter8/MiniMind-pretrain/minimind-v && git -C chapter8/MiniMind-pretrain/minimind-v fetch origin ead791c530fa5f9a3549dbfe9e11ec732d18d2e5 && git -`

- [ ] `git clone https://github.com/bojieli/minimind-v.git chapter8/MiniMind-pretrain/minimind-v && git -C chapter8/MiniMind-pretrain/minimind-v fetch origin ead791c530fa5f9a3549dbfe9e11ec732d18d2e5 && git -C chapter8/MiniMind-pretrain/minimind-v checkout --detach ead791c530fa5f9a3549dbfe9e11ec732d18d2e5 && test "$(git -C chapter8/MiniMind-pretrain/minimind-v rev-parse HEAD)" = "ead791c530fa5f9a3549dbfe9e11ec732d18d2e5"` (medium confidence, clone, README L203)
  - L201: `# 第 8 章 · 训练框架（bojieli/* 为本书适配的分支）`
  - L202: `git clone https://github.com/bojieli/minimind.git chapter8/MiniMind-pretrain/minimind && git -C chapter8/MiniMind-pretrain/minimind fetch origin 8bdc5d97d5845a8c1ac2ed56a5b8b4c0d0fb0795 && git -C chap`
  - L203: `git clone https://github.com/bojieli/minimind-v.git chapter8/MiniMind-pretrain/minimind-v && git -C chapter8/MiniMind-pretrain/minimind-v fetch origin ead791c530fa5f9a3549dbfe9e11ec732d18d2e5 && git -`
  - L204: `git clone https://github.com/bojieli/AdaptThink.git chapter8/AdaptThink-original && git -C chapter8/AdaptThink-original checkout --detach 0033ad172dd53ac64004b763477407014f21b838  # 实验 8-10`

- [ ] `git clone https://github.com/bojieli/AdaptThink.git chapter8/AdaptThink-original && git -C chapter8/AdaptThink-original checkout --detach 0033ad172dd53ac64004b763477407014f21b838` (medium confidence, clone, README L204)
  - L202: `git clone https://github.com/bojieli/minimind.git chapter8/MiniMind-pretrain/minimind && git -C chapter8/MiniMind-pretrain/minimind fetch origin 8bdc5d97d5845a8c1ac2ed56a5b8b4c0d0fb0795 && git -C chap`
  - L203: `git clone https://github.com/bojieli/minimind-v.git chapter8/MiniMind-pretrain/minimind-v && git -C chapter8/MiniMind-pretrain/minimind-v fetch origin ead791c530fa5f9a3549dbfe9e11ec732d18d2e5 && git -`
  - L204: `git clone https://github.com/bojieli/AdaptThink.git chapter8/AdaptThink-original && git -C chapter8/AdaptThink-original checkout --detach 0033ad172dd53ac64004b763477407014f21b838  # 实验 8-10`
  - L205: `git clone https://github.com/bojieli/SFTvsRL.git chapter8/SFTvsRL && git -C chapter8/SFTvsRL checkout --detach fef0a4a3367260a0934be1e40b01e4021698e023  # 实验 8-11、8-12`

- [ ] `git clone https://github.com/bojieli/SFTvsRL.git chapter8/SFTvsRL && git -C chapter8/SFTvsRL checkout --detach fef0a4a3367260a0934be1e40b01e4021698e023` (medium confidence, clone, README L205)
  - L203: `git clone https://github.com/bojieli/minimind-v.git chapter8/MiniMind-pretrain/minimind-v && git -C chapter8/MiniMind-pretrain/minimind-v fetch origin ead791c530fa5f9a3549dbfe9e11ec732d18d2e5 && git -`
  - L204: `git clone https://github.com/bojieli/AdaptThink.git chapter8/AdaptThink-original && git -C chapter8/AdaptThink-original checkout --detach 0033ad172dd53ac64004b763477407014f21b838  # 实验 8-10`
  - L205: `git clone https://github.com/bojieli/SFTvsRL.git chapter8/SFTvsRL && git -C chapter8/SFTvsRL checkout --detach fef0a4a3367260a0934be1e40b01e4021698e023  # 实验 8-11、8-12`
  - L206: `git clone https://github.com/bojieli/AWorld.git chapter8/AWorld && git -C chapter8/AWorld checkout --detach a52d61d6d483e66b22ef16970eae5bbf4f4ab2ec  # 实验 8-15`

- [ ] `git clone https://github.com/bojieli/AWorld.git chapter8/AWorld && git -C chapter8/AWorld checkout --detach a52d61d6d483e66b22ef16970eae5bbf4f4ab2ec` (medium confidence, clone, README L206)
  - L204: `git clone https://github.com/bojieli/AdaptThink.git chapter8/AdaptThink-original && git -C chapter8/AdaptThink-original checkout --detach 0033ad172dd53ac64004b763477407014f21b838  # 实验 8-10`
  - L205: `git clone https://github.com/bojieli/SFTvsRL.git chapter8/SFTvsRL && git -C chapter8/SFTvsRL checkout --detach fef0a4a3367260a0934be1e40b01e4021698e023  # 实验 8-11、8-12`
  - L206: `git clone https://github.com/bojieli/AWorld.git chapter8/AWorld && git -C chapter8/AWorld checkout --detach a52d61d6d483e66b22ef16970eae5bbf4f4ab2ec  # 实验 8-15`
  - L207: `git clone https://github.com/bojieli/verl.git chapter8/verl && git -C chapter8/verl checkout --detach 1593fc3a8cf894debdc3dece2a23ed739c282789  # 实验 8-14 ReTool 配方；8-15 训练后端`

- [ ] `git clone https://github.com/bojieli/verl.git chapter8/verl && git -C chapter8/verl checkout --detach 1593fc3a8cf894debdc3dece2a23ed739c282789` (medium confidence, clone, README L207)
  - L205: `git clone https://github.com/bojieli/SFTvsRL.git chapter8/SFTvsRL && git -C chapter8/SFTvsRL checkout --detach fef0a4a3367260a0934be1e40b01e4021698e023  # 实验 8-11、8-12`
  - L206: `git clone https://github.com/bojieli/AWorld.git chapter8/AWorld && git -C chapter8/AWorld checkout --detach a52d61d6d483e66b22ef16970eae5bbf4f4ab2ec  # 实验 8-15`
  - L207: `git clone https://github.com/bojieli/verl.git chapter8/verl && git -C chapter8/verl checkout --detach 1593fc3a8cf894debdc3dece2a23ed739c282789  # 实验 8-14 ReTool 配方；8-15 训练后端`
  - L208: `git clone https://github.com/bojieli/SandboxFusion.git chapter8/SandboxFusion && git -C chapter8/SandboxFusion fetch origin 4a0d573ebd64c98234c190a9d1d49e4276199a0c && git -C chapter8/SandboxFusion ch`

- [ ] `git clone https://github.com/bojieli/SandboxFusion.git chapter8/SandboxFusion && git -C chapter8/SandboxFusion fetch origin 4a0d573ebd64c98234c190a9d1d49e4276199a0c && git -C chapter8/SandboxFusion checkout --detach 4a0d573ebd64c98234c190a9d1d49e4276199a0c && test "$(git -C chapter8/SandboxFusion rev-parse HEAD)" = "4a0d573ebd64c98234c190a9d1d49e4276199a0c"` (medium confidence, clone, README L208)
  - L206: `git clone https://github.com/bojieli/AWorld.git chapter8/AWorld && git -C chapter8/AWorld checkout --detach a52d61d6d483e66b22ef16970eae5bbf4f4ab2ec  # 实验 8-15`
  - L207: `git clone https://github.com/bojieli/verl.git chapter8/verl && git -C chapter8/verl checkout --detach 1593fc3a8cf894debdc3dece2a23ed739c282789  # 实验 8-14 ReTool 配方；8-15 训练后端`
  - L208: `git clone https://github.com/bojieli/SandboxFusion.git chapter8/SandboxFusion && git -C chapter8/SandboxFusion fetch origin 4a0d573ebd64c98234c190a9d1d49e4276199a0c && git -C chapter8/SandboxFusion ch`
  - L209: `git clone https://github.com/thinking-machines-lab/tinker-cookbook.git chapter8/tinker-cookbook && git -C chapter8/tinker-cookbook checkout --detach fc8449187041cf102905f3f751e6d2eac7f9f754`

- [ ] `git clone https://github.com/thinking-machines-lab/tinker-cookbook.git chapter8/tinker-cookbook && git -C chapter8/tinker-cookbook checkout --detach fc8449187041cf102905f3f751e6d2eac7f9f754` (medium confidence, clone, README L209)
  - L207: `git clone https://github.com/bojieli/verl.git chapter8/verl && git -C chapter8/verl checkout --detach 1593fc3a8cf894debdc3dece2a23ed739c282789  # 实验 8-14 ReTool 配方；8-15 训练后端`
  - L208: `git clone https://github.com/bojieli/SandboxFusion.git chapter8/SandboxFusion && git -C chapter8/SandboxFusion fetch origin 4a0d573ebd64c98234c190a9d1d49e4276199a0c && git -C chapter8/SandboxFusion ch`
  - L209: `git clone https://github.com/thinking-machines-lab/tinker-cookbook.git chapter8/tinker-cookbook && git -C chapter8/tinker-cookbook checkout --detach fc8449187041cf102905f3f751e6d2eac7f9f754`
  - L210: `git clone https://github.com/19PINE-AI/rlvp.git chapter8/RLVP/rlvp && git -C chapter8/RLVP/rlvp fetch origin 1ad30bc7e338911fb733739393d92c420f4d8bee && git -C chapter8/RLVP/rlvp checkout --detach 1ad`

- [ ] `git clone https://github.com/19PINE-AI/rlvp.git chapter8/RLVP/rlvp && git -C chapter8/RLVP/rlvp fetch origin 1ad30bc7e338911fb733739393d92c420f4d8bee && git -C chapter8/RLVP/rlvp checkout --detach 1ad30bc7e338911fb733739393d92c420f4d8bee && test "$(git -C chapter8/RLVP/rlvp rev-parse HEAD)" = "1ad30bc7e338911fb733739393d92c420f4d8bee"` (medium confidence, clone, README L210)
  - L208: `git clone https://github.com/bojieli/SandboxFusion.git chapter8/SandboxFusion && git -C chapter8/SandboxFusion fetch origin 4a0d573ebd64c98234c190a9d1d49e4276199a0c && git -C chapter8/SandboxFusion ch`
  - L209: `git clone https://github.com/thinking-machines-lab/tinker-cookbook.git chapter8/tinker-cookbook && git -C chapter8/tinker-cookbook checkout --detach fc8449187041cf102905f3f751e6d2eac7f9f754`
  - L210: `git clone https://github.com/19PINE-AI/rlvp.git chapter8/RLVP/rlvp && git -C chapter8/RLVP/rlvp fetch origin 1ad30bc7e338911fb733739393d92c420f4d8bee && git -C chapter8/RLVP/rlvp checkout --detach 1ad`
  - L211: `git clone https://github.com/PRIME-RL/SimpleVLA-RL.git chapter8/SimpleVLA-RL/SimpleVLA-RL && git -C chapter8/SimpleVLA-RL/SimpleVLA-RL checkout --detach 7c51662df27b586f9e8a1ab35fcf849f2b8852f9  # 实验 `

- [ ] `git clone https://github.com/PRIME-RL/SimpleVLA-RL.git chapter8/SimpleVLA-RL/SimpleVLA-RL && git -C chapter8/SimpleVLA-RL/SimpleVLA-RL checkout --detach 7c51662df27b586f9e8a1ab35fcf849f2b8852f9` (medium confidence, clone, README L211)
  - L209: `git clone https://github.com/thinking-machines-lab/tinker-cookbook.git chapter8/tinker-cookbook && git -C chapter8/tinker-cookbook checkout --detach fc8449187041cf102905f3f751e6d2eac7f9f754`
  - L210: `git clone https://github.com/19PINE-AI/rlvp.git chapter8/RLVP/rlvp && git -C chapter8/RLVP/rlvp fetch origin 1ad30bc7e338911fb733739393d92c420f4d8bee && git -C chapter8/RLVP/rlvp checkout --detach 1ad`
  - L211: `git clone https://github.com/PRIME-RL/SimpleVLA-RL.git chapter8/SimpleVLA-RL/SimpleVLA-RL && git -C chapter8/SimpleVLA-RL/SimpleVLA-RL checkout --detach 7c51662df27b586f9e8a1ab35fcf849f2b8852f9  # 实验 `
  - L212: ``

- [ ] `git clone https://github.com/19PINE-AI/TalkAct.git chapter10/use-computer-while-calling && git -C chapter10/use-computer-while-calling fetch origin 7d70007f72d45ddfc1a14e8e229b6d444e4919a2 && git -C chapter10/use-computer-while-calling checkout --detach 7d70007f72d45ddfc1a14e8e229b6d444e4919a2 && test "$(git -C chapter10/use-computer-while-calling rev-parse HEAD)" = "7d70007f72d45ddfc1a14e8e229b6d444e4919a2"` (medium confidence, clone, README L214)
  - L212: ``
  - L213: `# 第 10 章 · 双 Agent 架构（已独立为 TalkAct 项目）+ 斯坦福 AI 小镇`
  - L214: `git clone https://github.com/19PINE-AI/TalkAct.git chapter10/use-computer-while-calling && git -C chapter10/use-computer-while-calling fetch origin 7d70007f72d45ddfc1a14e8e229b6d444e4919a2 && git -C c`
  - L215: `git clone https://github.com/joonspk-research/generative_agents.git chapter10/generative_agents && git -C chapter10/generative_agents fetch origin fe05a71d3e4ed7d10bf68aa4eda6dd995ec070f4 && git -C ch`

- [ ] `git clone https://github.com/joonspk-research/generative_agents.git chapter10/generative_agents && git -C chapter10/generative_agents fetch origin fe05a71d3e4ed7d10bf68aa4eda6dd995ec070f4 && git -C chapter10/generative_agents checkout --detach fe05a71d3e4ed7d10bf68aa4eda6dd995ec070f4 && test "$(git -C chapter10/generative_agents rev-parse HEAD)" = "fe05a71d3e4ed7d10bf68aa4eda6dd995ec070f4"` (medium confidence, clone, README L215)
  - L213: `# 第 10 章 · 双 Agent 架构（已独立为 TalkAct 项目）+ 斯坦福 AI 小镇`
  - L214: `git clone https://github.com/19PINE-AI/TalkAct.git chapter10/use-computer-while-calling && git -C chapter10/use-computer-while-calling fetch origin 7d70007f72d45ddfc1a14e8e229b6d444e4919a2 && git -C c`
  - L215: `git clone https://github.com/joonspk-research/generative_agents.git chapter10/generative_agents && git -C chapter10/generative_agents fetch origin fe05a71d3e4ed7d10bf68aa4eda6dd995ec070f4 && git -C ch`
  - L216: `````


### EverMind-AI/EverOS

- Repo: <https://github.com/EverMind-AI/EverOS>
- Commands: 2

- [ ] `brew install --cask libreoffice` (medium confidence, install, README L334)
  - L332: ``
  - L333: ````bash`
  - L334: `brew install --cask libreoffice              # macOS`
  - L335: `sudo apt-get install -y libreoffice          # Debian / Ubuntu`

- [ ] `git clone https://github.com/EverMind-AI/EverOS.git` (medium confidence, clone, README L341)
  - L339: ``
  - L340: ````bash`
  - L341: `git clone https://github.com/EverMind-AI/EverOS.git`
  - L342: `cd EverOS`


### HKUDS/DeepTutor

- Repo: <https://github.com/HKUDS/DeepTutor>
- Commands: 9

- [ ] `docker run --rm --name deeptutor -p 127.0.0.1:3782:3782 -v deeptutor-data:/app/data ghcr.io/hkuds/deeptutor:latest` (medium confidence, run, README L283)
  - L281: ``
  - L282: ````bash`
  - L283: `docker run --rm --name deeptutor \`
  - L284: `-p 127.0.0.1:3782:3782 \`

- [ ] `python -m pip install -U "deeptutor[full]"` (medium confidence, install, README L300)
  - L298: ````bash`
  - L299: `mkdir -p my-deeptutor && cd my-deeptutor`
  - L300: `python -m pip install -U "deeptutor[full]"`
  - L301: `deeptutor init     # ports + LLM provider + optional embedding/search`

- [ ] `git clone --branch dev https://github.com/HKUDS/DeepTutor.git` (medium confidence, clone, README L317)
  - L315: ``
  - L316: ````bash`
  - L317: `git clone --branch dev https://github.com/HKUDS/DeepTutor.git`
  - L318: `cd DeepTutor`

- [ ] `python -m pip install --upgrade pip` (medium confidence, install, README L320)
  - L318: `cd DeepTutor`
  - L319: `python3 -m venv .venv && source .venv/bin/activate`
  - L320: `python -m pip install --upgrade pip`
  - L321: `python -m pip install -r requirements/full.txt`

- [ ] `python -m pip install -r requirements/full.txt` (medium confidence, install, README L321)
  - L319: `python3 -m venv .venv && source .venv/bin/activate`
  - L320: `python -m pip install --upgrade pip`
  - L321: `python -m pip install -r requirements/full.txt`
  - L322: `python -m pip install -e . --no-deps`

- [ ] `python -m pip install -e . --no-deps` (medium confidence, install, README L322)
  - L320: `python -m pip install --upgrade pip`
  - L321: `python -m pip install -r requirements/full.txt`
  - L322: `python -m pip install -e . --no-deps`
  - L323: `( cd web && npm ci --legacy-peer-deps )`

- [ ] `python -m pip install -U deeptutor` (medium confidence, install, README L339)
  - L337: ````bash`
  - L338: `mkdir -p my-deeptutor && cd my-deeptutor`
  - L339: `python -m pip install -U deeptutor`
  - L340: `deeptutor init --cli`

- [ ] `python -m pip install -r requirements/full.txt` (medium confidence, install, README L828)
  - L826: ``
  - L827: ````bash`
  - L828: `python -m pip install -r requirements/full.txt`
  - L829: `python -m pip install -e . --no-deps`

- [ ] `python -m pip install -e . --no-deps` (medium confidence, install, README L829)
  - L827: ````bash`
  - L828: `python -m pip install -r requirements/full.txt`
  - L829: `python -m pip install -e . --no-deps`
  - L830: `````


### headroomlabs-ai/headroom

- Repo: <https://github.com/headroomlabs-ai/headroom>
- Commands: 11

- [ ] `pip install headroom-ai` (medium confidence, install, README L48)
  - L46: ``
  - L47: ````bash`
  - L48: `pip install headroom-ai`
  - L49: `````

- [ ] `pip install "headroom-ai[all]"` (medium confidence, install, README L133)
  - L131: `# 1 — Install`
  - L132: `uv tool install --python 3.13 "headroom-ai[all]"  # CLI in a self-contained env`
  - L133: `pip install "headroom-ai[all]"                    # Python — ships the `headroom` CLI`
  - L134: `npm install headroom-ai                           # TypeScript SDK only — no CLI`

- [ ] `npm install headroom-ai` (medium confidence, install, README L134)
  - L132: `uv tool install --python 3.13 "headroom-ai[all]"  # CLI in a self-contained env`
  - L133: `pip install "headroom-ai[all]"                    # Python — ships the `headroom` CLI`
  - L134: `npm install headroom-ai                           # TypeScript SDK only — no CLI`
  - L135: ``

- [ ] `pip install "headroom-ai[proxy]"` (medium confidence, install, README L378)
  - L376: ``
  - L377: ````bash`
  - L378: `pip install "headroom-ai[proxy]"`
  - L379: `headroom wrap vscode-claude`

- [ ] `pip install "headroom-ai[all]"` (high confidence, install, README L485)
  - L483: ````bash`
  - L484: `uv tool install --python 3.13 "headroom-ai[all]"  # CLI, isolated app env`
  - L485: `pip install "headroom-ai[all]"                    # CLI/proxy feature set`
  - L486: `npm install headroom-ai                           # TypeScript SDK (library only)`

- [ ] `npm install headroom-ai` (high confidence, install, README L486)
  - L484: `uv tool install --python 3.13 "headroom-ai[all]"  # CLI, isolated app env`
  - L485: `pip install "headroom-ai[all]"                    # CLI/proxy feature set`
  - L486: `npm install headroom-ai                           # TypeScript SDK (library only)`
  - L487: `docker pull ghcr.io/headroomlabs-ai/headroom:latest`

- [ ] `docker pull ghcr.io/headroomlabs-ai/headroom:latest` (high confidence, install, README L487)
  - L485: `pip install "headroom-ai[all]"                    # CLI/proxy feature set`
  - L486: `npm install headroom-ai                           # TypeScript SDK (library only)`
  - L487: `docker pull ghcr.io/headroomlabs-ai/headroom:latest`
  - L488: `````

- [ ] `brew install python@3.13` (high confidence, install, README L515)
  - L513: ``
  - L514: ````bash`
  - L515: `brew install python@3.13  # if 3.13 is not already available`
  - L516: `uv tool install --python 3.13 "headroom-ai[all]"`

- [ ] `brew install onnxruntime` (high confidence, install, README L613)
  - L611: ``
  - L612: ````bash`
  - L613: `brew install onnxruntime`
  - L614: `ORT_STRATEGY=system \`

- [ ] `pip install "headroom-ai[all]"` (high confidence, install, README L617)
  - L615: `ORT_LIB_LOCATION="$(brew --prefix onnxruntime)/lib" \`
  - L616: `ORT_PREFER_DYNAMIC_LINK=1 \`
  - L617: `pip install "headroom-ai[all]"`
  - L618: ``

- [ ] `git clone https://github.com/headroomlabs-ai/headroom.git && cd headroom` (medium confidence, clone, README L730)
  - L728: ``
  - L729: ````bash`
  - L730: `git clone https://github.com/headroomlabs-ai/headroom.git && cd headroom`
  - L731: `uv sync --extra dev && uv run pytest`


### didilili/ai-agents-from-zero

- Repo: <https://github.com/didilili/ai-agents-from-zero>
- Commands: 2

- [ ] `git clone https://github.com/didilili/ai-agents-from-zero.git` (medium confidence, clone, README L201)
  - L199: ``
  - L200: ````bash`
  - L201: `git clone https://github.com/didilili/ai-agents-from-zero.git`
  - L202: `cd ai-agents-from-zero`

- [ ] `pip install -r requirements.txt` (medium confidence, install, README L211)
  - L209: `source .venv/bin/activate          # macOS/Linux`
  - L210: `# .venv\Scripts\activate           # Windows CMD`
  - L211: `pip install -r requirements.txt`
  - L212: `````


### Osmantic/ODS

- Repo: <https://github.com/Osmantic/ODS>
- Commands: 2

- [ ] `git clone https://github.com/Osmantic/ODS.git` (medium confidence, clone, README L215)
  - L213: ``
  - L214: ````bash`
  - L215: `git clone https://github.com/Osmantic/ODS.git`
  - L216: `cd ODS/ods`

- [ ] `git clone https://github.com/Osmantic/ODS.git ~/src/ODS` (medium confidence, clone, README L255)
  - L253: ``
  - L254: ````bash`
  - L255: `git clone https://github.com/Osmantic/ODS.git ~/src/ODS`
  - L256: `cd ~/src/ODS/ods`


### rocketride-org/rocketride-server

- Repo: <https://github.com/rocketride-org/rocketride-server>
- Commands: 2

- [ ] `pip install rocketride` (medium confidence, install, README L124)
  - L122: ``
  - L123: ````bash`
  - L124: `pip install rocketride`
  - L125: `````

- [ ] `docker pull ghcr.io/rocketride-org/rocketride-engine:latest` (high confidence, install, README L188)
  - L186: ``
  - L187: ````bash`
  - L188: `docker pull ghcr.io/rocketride-org/rocketride-engine:latest`
  - L189: `docker create --name rocketride-engine -p 127.0.0.1:5565:5565 ghcr.io/rocketride-org/rocketride-engine:latest`


### Graphify-Labs/graphify

- Repo: <https://github.com/Graphify-Labs/graphify>
- Commands: 2

- [ ] `brew install python@3.12 uv` (medium confidence, install, README L197)
  - L195: `**macOS quick install (Homebrew):**`
  - L196: ````bash`
  - L197: `brew install python@3.12 uv`
  - L198: `````

- [ ] `pip install graphifyy` (high confidence, install, README L229) **⚠ caution**
  - L227: `uv tool install graphifyy   # recommended, isolated env (if 'graphify' isn't found after, run: uv tool update-shell)`
  - L228: `pipx install graphifyy      # alternative`
  - L229: `pip install graphifyy       # may need PATH setup, see Troubleshooting below`
  - L230: `````


### virgiliojr94/book-to-skill

- Repo: <https://github.com/virgiliojr94/book-to-skill>
- Commands: 1

- [ ] `git clone https://github.com/virgiliojr94/book-to-skill.git ~/.claude/skills/book-to-skill` (high confidence, clone, README L163)
  - L161: ``
  - L162: `# Or manually — clone into your skills folder (registers /book-to-skill):`
  - L163: `git clone https://github.com/virgiliojr94/book-to-skill.git ~/.claude/skills/book-to-skill`
  - L164: `# (Copilot CLI: ~/.copilot/skills/ · Amp/cross-agent: ~/.agents/skills/)`


### WenyuChiou/awesome-agentic-ai-zh

- Repo: <https://github.com/WenyuChiou/awesome-agentic-ai-zh>
- Commands: 1

- [ ] `git clone https://github.com/WenyuChiou/awesome-agentic-ai-zh.git` (medium confidence, clone, README L63)
  - L61: ``
  - L62: ````powershell`
  - L63: `git clone https://github.com/WenyuChiou/awesome-agentic-ai-zh.git`
  - L64: `cd awesome-agentic-ai-zh`


### StarTrail-org/PixelRAG

- Repo: <https://github.com/StarTrail-org/PixelRAG>
- Commands: 7

- [ ] `pip install pixelrag` (medium confidence, install, README L40)
  - L38: ``
  - L39: ````bash`
  - L40: `pip install pixelrag`
  - L41: `````

- [ ] `pip install 'pixelrag[serve]'` (medium confidence, install, README L144)
  - L142: ``
  - L143: ````bash`
  - L144: `pip install 'pixelrag[serve]'`
  - L145: ``

- [ ] `pip install 'pixelrag[index]'` (high confidence, install, README L164)
  - L162: ``
  - L163: ````bash`
  - L164: `pip install 'pixelrag[index]'`
  - L165: ``

- [ ] `pip install 'pixelrag[index,pdf]'` (high confidence, install, README L193)
  - L191: ``
  - L192: ````bash`
  - L193: `pip install 'pixelrag[index,pdf]'`
  - L194: ``

- [ ] `pip install 'pixelrag[embed]'` (medium confidence, install, README L264)
  - L262: ``
  - L263: ````bash`
  - L264: `pip install 'pixelrag[embed]'`
  - L265: ``

- [ ] `pip install 'pixelrag[serve,qdrant]'` (medium confidence, install, README L291)
  - L289: ``
  - L290: ````bash`
  - L291: `pip install 'pixelrag[serve,qdrant]'   # or 'pixelrag[index,qdrant]'`
  - L292: ``

- [ ] `docker compose up --build` (high confidence, run, README L339)
  - L337: `pixelrag index build   # writes index.faiss, metadata.npz and articles.json to ./data/index`
  - L338: ``
  - L339: `docker compose up --build`
  - L340: `# then query it`


### ForeactLabs/OpenExecutive

- Repo: <https://github.com/ForeactLabs/OpenExecutive>
- Commands: 3

- [ ] `git clone https://github.com/ForeactLabs/OpenExecutive.git` (high confidence, clone, README L134)
  - L132: ````bash`
  - L133: `# Clone the repo`
  - L134: `git clone https://github.com/ForeactLabs/OpenExecutive.git`
  - L135: `cd OpenExecutive`

- [ ] `make install` (high confidence, install, README L138)
  - L136: ``
  - L137: `# Install the backend and web app dependencies`
  - L138: `make install`
  - L139: ``

- [ ] `npm install` (high confidence, install, README L189)
  - L187: `# In a second terminal`
  - L188: `cd packages/ui`
  - L189: `npm install`
  - L190: `npm run dev`

---

## Sign-off

- Reviewed by: ______________________  Date: ____________
- Repos reviewed: ______ / 46
- Commands judged correct: ______ / 184
- False positives / notes:
  - 
