# Extraction spot-check (human review)

_Generated 2026-11-25 from `C:\Users\asusj\.github-tool\github-tool.db`._

Sampled **50 repositories** and **158 install commands**; **4** commands sit near caution words (for example / e.g. / alternative / deprecated). This is the optional independent human spot-check from the roadmap (Phase 6). The automated source-line check and an agent semantic review already passed; this packet is for a person to confirm semantic trustworthiness on a sample.

## How to review

1. For each repository, open the GitHub URL.
2. For each command, read the cited README line (and the quoted context) and decide whether it is a genuine install/run/build/clone instruction **for that repository**.
3. Tick the box if it is correct. Leave it unticked and note the reason if it is an example for a sub-component, a template, or otherwise misleading.
4. Record the result at the bottom and file this document with the validation notes.

> Tip: `⚠ caution` marks commands whose nearby lines contain hedging words; check those first.

---
### redis/redis

- Repo: <https://github.com/redis/redis>
- Language: C
- Commands: 6

- [ ] `docker run -d -p 6379:6379 redis:latest` (high confidence, run, README L93)
  - L91: `- [**Official Redis Docker images (Alpine/Debian)**](https://hub.docker.com/_/redis)`
  - L92: ````sh`
  - L93: `docker run -d -p 6379:6379 redis:latest`
  - L94: `````

- [ ] `git clone https://github.com/redis/redis.git && cd redis` (medium confidence, clone, README L234)
  - L232: ``
  - L233: `# B) git checkout — clone the bundled modules once:`
  - L234: `git clone https://github.com/redis/redis.git && cd redis`
  - L235: `make modules-update`

- [ ] `docker build -f docker/Dockerfile.noble -t redis-build:noble .` (high confidence, build, README L252)
  - L250: ``
  - L251: ````bash`
  - L252: `docker build -f docker/Dockerfile.noble -t redis-build:noble .`
  - L253: ``

- [ ] `docker run --rm -it -v "$PWD":/workspace -w /workspace redis-build:noble bash -lc 'make -j"$(nproc)" && make run'` (high confidence, run, README L259)
  - L257: ``
  - L258: `# Build with the working tree mounted:`
  - L259: `docker run --rm -it -v "$PWD":/workspace -w /workspace redis-build:noble \`
  - L260: `bash -lc 'make -j"$(nproc)" && make run'`

- [ ] `make install PREFIX=/usr/local` (high confidence, install, README L326)
  - L324: ``
  - L325: ````sh`
  - L326: `make install PREFIX=/usr/local          # core binaries + every built module`
  - L327: `sudo make install                       # same, into the default /usr/local`

- [ ] `make build redis` (high confidence, build, README L361)
  - L359: ``
  - L360: ````sh`
  - L361: `make build redis`
  - L362: `````


### tfussell/xlnt

- Repo: <https://github.com/tfussell/xlnt>
- Language: C++
- Commands: 1

- [ ] `git clone https://github.com/microsoft/vcpkg.git` (medium confidence, clone, README L43)
  - L41: `You can download and install xlnt using the [vcpkg](https://github.com/microsoft/vcpkg) dependency manager:`
  - L42: ``
  - L43: `git clone https://github.com/microsoft/vcpkg.git`
  - L44: `cd vcpkg`


### dolthub/dolt

- Repo: <https://github.com/dolthub/dolt>
- Language: Go
- Commands: 2

- [ ] `brew install dolt` (medium confidence, install, README L139)
  - L137: ``
  - L138: `````
  - L139: `brew install dolt`
  - L140: `````

- [ ] `go install ./cmd/dolt` (medium confidence, install, README L180)
  - L178: ``
  - L179: `````
  - L180: `go install ./cmd/dolt`
  - L181: `````


### microsoft/TypeChat

- Repo: <https://github.com/microsoft/TypeChat>
- Language: JavaScript
- Commands: 1

- [ ] `npm install typechat` (high confidence, install, README L32)
  - L30: ``
  - L31: `````
  - L32: `npm install typechat`
  - L33: `````


### deepset-ai/haystack

- Repo: <https://github.com/deepset-ai/haystack>
- Language: Python
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


### microsoft/aici

- Repo: <https://github.com/microsoft/aici>
- Language: Rust
- Commands: 2

- [ ] `brew install git cmake ccache` (low confidence, install, README L77)
  - L75: `or using Homebrew on macOS:`
  - L76: ``
  - L77: `brew install git cmake ccache`
  - L78: ``

- [ ] `pip install pytest pytest-forked ujson posix_ipc numpy requests` (low confidence, install, README L95)
  - L93: `Last, to work with **Python** controllers and scripts (like this tutorial), run this command to install the required packages:`
  - L94: ``
  - L95: `pip install pytest pytest-forked ujson posix_ipc numpy requests`
  - L96: ``


### langfuse/langfuse

- Repo: <https://github.com/langfuse/langfuse>
- Language: TypeScript
- Commands: 3

- [ ] `git clone --depth=1 https://github.com/langfuse/langfuse.git` (medium confidence, clone, README L109)
  - L107: ````bash`
  - L108: `# Get a copy of the latest Langfuse repository`
  - L109: `git clone --depth=1 https://github.com/langfuse/langfuse.git`
  - L110: `cd langfuse`

- [ ] `docker compose up` (medium confidence, run, README L113)
  - L111: ``
  - L112: `# Run the langfuse docker compose`
  - L113: `docker compose up`
  - L114: `````

- [ ] `pip install langfuse openai` (medium confidence, install, README L210)
  - L208: ``
  - L209: ````bash`
  - L210: `pip install langfuse openai`
  - L211: `````


### psycopg/psycopg2

- Repo: <https://github.com/psycopg/psycopg2>
- Language: C
- Commands: 2

- [ ] `pip install psycopg2` (low confidence, install, README L56)
  - L54: `package, using ``pip`` to download it from PyPI_::`
  - L55: ``
  - L56: `$ pip install psycopg2`
  - L57: ``

- [ ] `pip install psycopg2-binary` (low confidence, install, README L66)
  - L64: `external libraries, by installing the `psycopg2-binary`_ package from PyPI::`
  - L65: ``
  - L66: `$ pip install psycopg2-binary`
  - L67: ``


### manticoresoftware/manticoresearch

- Repo: <https://github.com/manticoresoftware/manticoresearch>
- Language: C++
- Commands: 2

- [ ] `docker run --name manticore --rm -d manticoresearch/manticore && until docker logs manticore 2>&1 | grep -q "accepting connections"; do sleep 1; done && docker exec -it manticore mysql && docker stop manticore` (medium confidence, run, README L180)
  - L178: ``
  - L179: `````
  - L180: `docker run --name manticore --rm -d manticoresearch/manticore && until docker logs manticore 2>&1 | grep -q "accepting connections"; do sleep 1; done && docker exec -it manticore mysql && docker stop `
  - L181: `````

- [ ] `brew install manticoresoftware/tap/manticore` (medium confidence, install, README L231)
  - L229: ``
  - L230: `````
  - L231: `brew install manticoresoftware/tap/manticore`
  - L232: `````


### infiniflow/ragflow

- Repo: <https://github.com/infiniflow/ragflow>
- Language: Go
- Commands: 3

- [ ] `git clone https://github.com/infiniflow/ragflow.git` (medium confidence, clone, README L182)
  - L180: ``
  - L181: ````bash`
  - L182: `git clone https://github.com/infiniflow/ragflow.git`
  - L183: `````

- [ ] `git clone https://github.com/infiniflow/ragflow.git` (high confidence, clone, README L248)
  - L246: ``
  - L247: ````bash`
  - L248: `git clone https://github.com/infiniflow/ragflow.git`
  - L249: `cd ragflow`

- [ ] `npm install` (high confidence, install, README L292)
  - L290: ````bash`
  - L291: `cd web`
  - L292: `npm install`
  - L293: `````


### poloclub/transformer-explainer

- Repo: <https://github.com/poloclub/transformer-explainer>
- Language: JavaScript
- Commands: 2

- [ ] `git clone https://github.com/poloclub/transformer-explainer.git` (medium confidence, clone, README L29)
  - L27: ``
  - L28: ````bash`
  - L29: `git clone https://github.com/poloclub/transformer-explainer.git`
  - L30: `cd transformer-explainer`

- [ ] `npm install` (medium confidence, install, README L31)
  - L29: `git clone https://github.com/poloclub/transformer-explainer.git`
  - L30: `cd transformer-explainer`
  - L31: `npm install`
  - L32: `npm run dev`


### neuml/txtai

- Repo: <https://github.com/neuml/txtai>
- Language: Python
- Commands: 1

- [ ] `pip install txtai` (high confidence, install, README L190)
  - L188: ``
  - L189: `````
  - L190: `pip install txtai`
  - L191: `````


### StarlightSearch/EmbedAnything

- Repo: <https://github.com/StarlightSearch/EmbedAnything>
- Language: Rust
- Commands: 2

- [ ] `pip install embed-anything` (medium confidence, install, README L365)
  - L363: ``
  - L364: ```
  - L365: `pip install embed-anything`
  - L366: ``<br/>`

- [ ] `pip install embed-anything-gpu` (medium confidence, install, README L371)
  - L369: ``
  - L370: ```
  - L371: `pip install embed-anything-gpu`
  - L372: ```


### CopilotKit/CopilotKit

- Repo: <https://github.com/CopilotKit/CopilotKit>
- Language: TypeScript
- Commands: 1

- [ ] `npm install @copilotkit/react-core @copilotkit/runtime` (high confidence, install, README L82)
  - L80: ``
  - L81: ````bash`
  - L82: `npm install @copilotkit/react-core @copilotkit/runtime`
  - L83: `````


### citusdata/citus

- Repo: <https://github.com/citusdata/citus>
- Language: C
- Commands: 1

- [ ] `docker run -d --name citus -p 5500:5432 -e POSTGRES_PASSWORD=mypassword citusdata/citus` (high confidence, run, README L80)
  - L78: ````bash`
  - L79: `# run PostgreSQL with Citus on port 5500`
  - L80: `docker run -d --name citus -p 5500:5432 -e POSTGRES_PASSWORD=mypassword citusdata/citus`
  - L81: ``


### vxcontrol/pentagi

- Repo: <https://github.com/vxcontrol/pentagi>
- Language: Go
- Commands: 11

- [ ] `docker compose up -d` (medium confidence, run, README L865)
  - L863: ````bash`
  - L864: `curl -O https://raw.githubusercontent.com/vxcontrol/pentagi/master/docker-compose.yml`
  - L865: `docker compose up -d`
  - L866: `````

- [ ] `docker compose up -d --force-recreate` (medium confidence, run, README L928)
  - L926: ````bash`
  - L927: `docker compose down`
  - L928: `docker compose up -d --force-recreate`
  - L929: `````

- [ ] `go install github.com/swaggo/swag/cmd/swag@v1.8.7` (high confidence, install, README L3154)
  - L3152: ``
  - L3153: ````bash`
  - L3154: `go install github.com/swaggo/swag/cmd/swag@v1.8.7`
  - L3155: `````

- [ ] `pnpm add -g fern-api` (high confidence, install, README L3180)
  - L3178: ``
  - L3179: ````bash`
  - L3180: `pnpm add -g fern-api`
  - L3181: `````

- [ ] `pnpm add -g graphql-codegen` (high confidence, install, README L3196)
  - L3194: ``
  - L3195: ````bash`
  - L3196: `pnpm add -g graphql-codegen`
  - L3197: `````

- [ ] `docker run --rm -v $(pwd)/.env:/opt/pentagi/.env vxcontrol/pentagi /opt/pentagi/bin/ctester -verbose` (medium confidence, run, README L3360)
  - L3358: ````bash`
  - L3359: `# Using Docker to test with default environment`
  - L3360: `docker run --rm -v $(pwd)/.env:/opt/pentagi/.env vxcontrol/pentagi /opt/pentagi/bin/ctester -verbose`
  - L3361: ``

- [ ] `docker run --rm -v $(pwd)/.env:/opt/pentagi/.env -v $(pwd)/my-config.yml:/opt/pentagi/config.yml vxcontrol/pentagi /opt/pentagi/bin/ctester -config /opt/pentagi/config.yml -agents simple,primary_agent,coder -verbose` (medium confidence, run, README L3363)
  - L3361: ``
  - L3362: `# Test with your custom provider configuration`
  - L3363: `docker run --rm \`
  - L3364: `-v $(pwd)/.env:/opt/pentagi/.env \`

- [ ] `docker run --rm -v $(pwd)/.env:/opt/pentagi/.env -v $(pwd):/opt/pentagi/output vxcontrol/pentagi /opt/pentagi/bin/ctester -report /opt/pentagi/output/report.md` (medium confidence, run, README L3369)
  - L3367: ``
  - L3368: `# Generate a detailed report`
  - L3369: `docker run --rm \`
  - L3370: `-v $(pwd)/.env:/opt/pentagi/.env \`

- [ ] `docker build --build-arg PACKAGE_VER=$PACKAGE_VER --build-arg PACKAGE_REV=$PACKAGE_REV -t pentagi:$PACKAGE_VERSION_FULL .` (medium confidence, build, README L4169)
  - L4167: ``
  - L4168: `# Standard build`
  - L4169: `docker build \`
  - L4170: `--build-arg PACKAGE_VER=$PACKAGE_VER \`

- [ ] `docker build `` (medium confidence, build, README L4197)
  - L4195: ``
  - L4196: `# Standard build`
  - L4197: `docker build ``
  - L4198: `--build-arg PACKAGE_VER=$env:PACKAGE_VER ``

- [ ] `docker build -t pentagi:dev .` (high confidence, build, README L4215)
  - L4213: ``
  - L4214: ````bash`
  - L4215: `docker build -t pentagi:dev .`
  - L4216: `````


### ConardLi/easy-dataset

- Repo: <https://github.com/ConardLi/easy-dataset>
- Language: JavaScript
- Commands: 7

- [ ] `git clone https://github.com/ConardLi/easy-dataset.git` (high confidence, clone, README L147)
  - L145: ``
  - L146: ````bash`
  - L147: `git clone https://github.com/ConardLi/easy-dataset.git`
  - L148: `cd easy-dataset`

- [ ] `npm install` (high confidence, install, README L154)
  - L152: ``
  - L153: ````bash`
  - L154: `npm install`
  - L155: `````

- [ ] `git clone https://github.com/ConardLi/easy-dataset.git` (medium confidence, clone, README L172)
  - L170: ``
  - L171: ````bash`
  - L172: `git clone https://github.com/ConardLi/easy-dataset.git`
  - L173: `cd easy-dataset`

- [ ] `docker-compose up -d` (medium confidence, run, README L198)
  - L196: ``
  - L197: ````bash`
  - L198: `docker-compose up -d`
  - L199: `````

- [ ] `git clone https://github.com/ConardLi/easy-dataset.git` (high confidence, clone, README L210)
  - L208: ``
  - L209: ````bash`
  - L210: `git clone https://github.com/ConardLi/easy-dataset.git`
  - L211: `cd easy-dataset`

- [ ] `docker build -t easy-dataset .` (high confidence, build, README L217)
  - L215: ``
  - L216: ````bash`
  - L217: `docker build -t easy-dataset .`
  - L218: `````

- [ ] `docker run -d -p 1717:1717 -v ./local-db:/app/local-db -v ./prisma:/app/prisma --name easy-dataset easy-dataset` (high confidence, run, README L223)
  - L221: ``
  - L222: ````bash`
  - L223: `docker run -d \`
  - L224: `-p 1717:1717 \`


### superduper-io/superduper

- Repo: <https://github.com/superduper-io/superduper>
- Language: Python
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


### trymirai/uzu

- Repo: <https://github.com/trymirai/uzu>
- Language: Rust
- Commands: 3

- [ ] `uv add uzu==0.7.5` (high confidence, install, README L85)
  - L83: ``
  - L84: ````bash`
  - L85: `uv add uzu==0.7.5`
  - L86: `````

- [ ] `pnpm add @trymirai/uzu@0.7.5` (high confidence, install, README L192)
  - L190: ``
  - L191: ````bash`
  - L192: `pnpm add @trymirai/uzu@0.7.5`
  - L193: `````

- [ ] `git clone https://github.com/trymirai/lalamo.git` (medium confidence, clone, README L1441)
  - L1439: ``
  - L1440: ````bash`
  - L1441: `git clone https://github.com/trymirai/lalamo.git`
  - L1442: `cd lalamo`


### OpenHands/OpenHands

- Repo: <https://github.com/OpenHands/OpenHands>
- Language: TypeScript
- Commands: 3

- [ ] `npm install -g @openhands/agent-canvas` (medium confidence, install, README L70)
  - L68: ``
  - L69: ````sh`
  - L70: `npm install -g @openhands/agent-canvas`
  - L71: `agent-canvas`

- [ ] `npm install -g @openhands/agent-canvas` (medium confidence, install, README L161)
  - L159: ``
  - L160: ````sh`
  - L161: `npm install -g @openhands/agent-canvas`
  - L162: `OH_CONVERSATION_RUNTIME=docker agent-canvas`

- [ ] `git clone https://github.com/OpenHands/OpenHands.git` (medium confidence, clone, README L183)
  - L181: ``
  - L182: ````sh`
  - L183: `git clone https://github.com/OpenHands/OpenHands.git`
  - L184: `cd OpenHands`


### timescale/timescaledb

- Repo: <https://github.com/timescale/timescaledb>
- Language: C
- Commands: 2

- [ ] `docker run -d --name timescaledb -p 6543:5432 -e POSTGRES_PASSWORD=password timescale/timescaledb-ha:pg18` (medium confidence, run, README L62)
  - L60: ``
  - L61: ````bash`
  - L62: `docker run -d --name timescaledb \`
  - L63: `-p 6543:5432 \`

- [ ] `docker run -d --name timescaledb -p 6543:5432 -e POSTGRES_PASSWORD=password timescale/timescaledb-ha:pg18` (medium confidence, run, README L412)
  - L410: `curl -sL https://tsdb.co/start-local | sh`
  - L411: `# Option 2: Use manual Docker command`
  - L412: `docker run -d --name timescaledb -p 6543:5432 -e POSTGRES_PASSWORD=password timescale/timescaledb-ha:pg18`
  - L413: `````


### Gaurav-Gosain/tuios

- Repo: <https://github.com/Gaurav-Gosain/tuios>
- Language: Go
- Commands: 5

- [ ] `brew install tuios` (medium confidence, install, README L73)
  - L71: `**Homebrew (macOS/Linux):**`
  - L72: ````bash`
  - L73: `brew install tuios`
  - L74: `````

- [ ] `brew install gaurav-gosain/tap/tuios-ghostty` (medium confidence, install, README L79) **⚠ caution**
  - L77: ````bash`
  - L78: `brew uninstall tuios`
  - L79: `brew install gaurav-gosain/tap/tuios-ghostty`
  - L80: `````

- [ ] `go install github.com/Gaurav-Gosain/tuios/cmd/tuios@latest` (medium confidence, install, README L103)
  - L101: ``
  - L102: `# Go install`
  - L103: `go install github.com/Gaurav-Gosain/tuios/cmd/tuios@latest`
  - L104: ``

- [ ] `docker run -it --rm ghcr.io/gaurav-gosain/tuios:latest` (medium confidence, run, README L106)
  - L104: ``
  - L105: `# Docker`
  - L106: `docker run -it --rm ghcr.io/gaurav-gosain/tuios:latest`
  - L107: `````

- [ ] `git clone https://github.com/gaurav-gosain/tuios.git` (medium confidence, clone, README L361)
  - L359: ``
  - L360: ````bash`
  - L361: `git clone https://github.com/gaurav-gosain/tuios.git`
  - L362: `cd tuios`


### dataease/SQLBot

- Repo: <https://github.com/dataease/SQLBot>
- Language: JavaScript
- Commands: 1

- [ ] `docker run -d --name sqlbot --restart unless-stopped -p 8000:8000 -p 8001:8001 -v ./data/sqlbot/excel:/opt/sqlbot/data/excel -v ./data/sqlbot/file:/opt/sqlbot/data/file -v ./data/sqlbot/images:/opt/sqlbot/images -v ./data/sqlbot/logs:/opt/sqlbot/app/logs -v ./data/postgresql:/var/lib/postgresql/data --privileged=true dataease/sqlbot` (medium confidence, run, README L40)
  - L38: ``
  - L39: ````bash`
  - L40: `docker run -d \`
  - L41: `--name sqlbot \`


### langchain-ai/langchain

- Repo: <https://github.com/langchain-ai/langchain>
- Language: Python
- Commands: 1

- [ ] `uv add langchain` (high confidence, install, README L32)
  - L30: ``
  - L31: ````bash`
  - L32: `uv add langchain`
  - L33: `````


### AntigmaLabs/ante

- Repo: <https://github.com/AntigmaLabs/ante>
- Language: Rust
- Commands: 1

- [ ] `cargo install ante-acp ante-gateway` (high confidence, install, README L247)
  - L245: ``
  - L246: ````sh`
  - L247: `cargo install ante-acp ante-gateway`
  - L248: `````


### ItzCrazyKns/Vane

- Repo: <https://github.com/ItzCrazyKns/Vane>
- Language: TypeScript
- Commands: 7

- [ ] `docker run -d -p 3000:3000 -v vane-data:/home/vane/data --name vane itzcrazykns1337/vane:latest` (high confidence, run, README L71)
  - L69: ``
  - L70: ````bash`
  - L71: `docker run -d -p 3000:3000 -v vane-data:/home/vane/data --name vane itzcrazykns1337/vane:latest`
  - L72: `````

- [ ] `docker run -d -p 3000:3000 -e SEARXNG_API_URL=http://your-searxng-url:8080 -v vane-data:/home/vane/data --name vane itzcrazykns1337/vane:slim-latest` (medium confidence, run, README L83)
  - L81: ``
  - L82: ````bash`
  - L83: `docker run -d -p 3000:3000 -e SEARXNG_API_URL=http://your-searxng-url:8080 -v vane-data:/home/vane/data --name vane itzcrazykns1337/vane:slim-latest`
  - L84: `````

- [ ] `git clone https://github.com/ItzCrazyKns/Vane.git` (high confidence, clone, README L101)
  - L99: ``
  - L100: ````bash`
  - L101: `git clone https://github.com/ItzCrazyKns/Vane.git`
  - L102: `````

- [ ] `docker build -t vane .` (high confidence, build, README L109)
  - L107: ``
  - L108: ````bash`
  - L109: `docker build -t vane .`
  - L110: `docker run -d -p 3000:3000 -v vane-data:/home/vane/data --name vane vane`

- [ ] `docker run -d -p 3000:3000 -v vane-data:/home/vane/data --name vane vane` (high confidence, run, README L110)
  - L108: ````bash`
  - L109: `docker build -t vane .`
  - L110: `docker run -d -p 3000:3000 -v vane-data:/home/vane/data --name vane vane`
  - L111: `````

- [ ] `git clone https://github.com/ItzCrazyKns/Vane.git` (high confidence, clone, README L123)
  - L121: ``
  - L122: ````bash`
  - L123: `git clone https://github.com/ItzCrazyKns/Vane.git`
  - L124: `cd Vane`

- [ ] `npm i` (high confidence, install, README L130)
  - L128: ``
  - L129: ````bash`
  - L130: `npm i`
  - L131: `````


### taosdata/TDengine

- Repo: <https://github.com/taosdata/TDengine>
- Language: C
- Commands: 1

- [ ] `git clone https://github.com/taosdata/TDengine.git` (high confidence, clone, README L132)
  - L130: ``
  - L131: ````bash`
  - L132: `git clone https://github.com/taosdata/TDengine.git`
  - L133: `cd TDengine`


### AIPentest/CyberStrikeAI

- Repo: <https://github.com/AIPentest/CyberStrikeAI>
- Language: Go
- Commands: 2

- [ ] `git clone https://github.com/Ed1s0nZ/CyberStrikeAI.git` (high confidence, clone, README L200)
  - L198: `**One-Command Deployment:**`
  - L199: ````bash`
  - L200: `git clone https://github.com/Ed1s0nZ/CyberStrikeAI.git`
  - L201: `cd CyberStrikeAI`

- [ ] `brew install nmap masscan sqlmap nikto gobuster ffuf hydra hashcat nuclei subfinder` (high confidence, install, README L244)
  - L242: `**macOS (Homebrew):**`
  - L243: ````bash`
  - L244: `brew install nmap masscan sqlmap nikto gobuster ffuf hydra hashcat nuclei subfinder`
  - L245: `````


### decolua/9router

- Repo: <https://github.com/decolua/9router>
- Language: JavaScript
- Commands: 11

- [ ] `npm install -g 9router` (high confidence, install, README L79)
  - L77: ``
  - L78: ````bash`
  - L79: `npm install -g 9router`
  - L80: `9router`

- [ ] `npm install` (high confidence, install, README L106)
  - L104: ````bash`
  - L105: `cp .env.example .env`
  - L106: `npm install`
  - L107: `PORT=20128 NEXT_PUBLIC_BASE_URL=http://localhost:20128 npm run dev`

- [ ] `pip install "headroom-ai[proxy]"` (medium confidence, install, README L584)
  - L582: ``
  - L583: ````bash`
  - L584: `pip install "headroom-ai[proxy]"`
  - L585: `headroom proxy --port 8787`

- [ ] `git clone https://github.com/decolua/9router.git` (medium confidence, clone, README L1252)
  - L1250: ````bash`
  - L1251: `# Clone and install`
  - L1252: `git clone https://github.com/decolua/9router.git`
  - L1253: `cd 9router`

- [ ] `npm install` (medium confidence, install, README L1254)
  - L1252: `git clone https://github.com/decolua/9router.git`
  - L1253: `cd 9router`
  - L1254: `npm install`
  - L1255: `npm run build`

- [ ] `npm install -g pm2` (medium confidence, install, README L1273)
  - L1271: ``
  - L1272: `# Or use PM2`
  - L1273: `npm install -g pm2`
  - L1274: `pm2 start npm --name 9router -- start`

- [ ] `docker run -d --name 9router -p 20128:20128 -v "$HOME/.9router:/app/data" -e DATA_DIR=/app/data decolua/9router:latest` (medium confidence, run, README L1289)
  - L1287: ``
  - L1288: ````bash`
  - L1289: `docker run -d \`
  - L1290: `--name 9router \`

- [ ] `git clone https://github.com/decolua/9router.git` (medium confidence, clone, README L1302)
  - L1300: ``
  - L1301: ````bash`
  - L1302: `git clone https://github.com/decolua/9router.git`
  - L1303: `cd 9router/app`

- [ ] `docker build -t 9router .` (medium confidence, build, README L1304)
  - L1302: `git clone https://github.com/decolua/9router.git`
  - L1303: `cd 9router/app`
  - L1304: `docker build -t 9router .`
  - L1305: `docker run -d --name 9router -p 20128:20128 \`

- [ ] `docker run -d --name 9router -p 20128:20128 -v "$HOME/.9router:/app/data" -e DATA_DIR=/app/data 9router` (medium confidence, run, README L1305)
  - L1303: `cd 9router/app`
  - L1304: `docker build -t 9router .`
  - L1305: `docker run -d --name 9router -p 20128:20128 \`
  - L1306: `-v "$HOME/.9router:/app/data" -e DATA_DIR=/app/data 9router`

- [ ] `docker pull decolua/9router:latest` (medium confidence, install, README L1320)
  - L1318: `docker restart 9router`
  - L1319: `docker stop 9router && docker rm 9router`
  - L1320: `docker pull decolua/9router:latest   # update to latest`
  - L1321: `````


### run-llama/llama_index

- Repo: <https://github.com/run-llama/llama_index>
- Language: Python
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


### chrishayuk/larql

- Repo: <https://github.com/chrishayuk/larql>
- Language: Rust
- Commands: 1

- [ ] `git clone https://github.com/chrishayuk/larql && cd larql` (high confidence, clone, README L44)
  - L42: ``
  - L43: ````bash`
  - L44: `git clone https://github.com/chrishayuk/larql && cd larql`
  - L45: `cargo build --release -p larql-cli -p larql-server   # Linux/Windows: add --no-default-features`


### firecrawl/firecrawl

- Repo: <https://github.com/firecrawl/firecrawl>
- Language: TypeScript
- Commands: 3

- [ ] `cargo install firecrawl-local` (medium confidence, install, README L61)
  - L59: ``
  - L60: ````bash`
  - L61: `cargo install firecrawl-local`
  - L62: `````

- [ ] `pip install firecrawl` (medium confidence, install, README L474)
  - L472: ``
  - L473: ````bash`
  - L474: `pip install firecrawl`
  - L475: `````

- [ ] `npm install firecrawl` (medium confidence, install, README L503)
  - L501: ``
  - L502: ````bash`
  - L503: `npm install firecrawl`
  - L504: `````


### orioledb/orioledb

- Repo: <https://github.com/orioledb/orioledb>
- Language: C
- Commands: 4

- [ ] `docker pull orioledb/orioledb:latest-pg17` (medium confidence, install, README L99)
  - L97: ``
  - L98: `````
  - L99: `docker pull orioledb/orioledb:latest-pg17`
  - L100: `````

- [ ] `docker run --name some-postgres -e POSTGRES_PASSWORD=... -e POSTGRES_INITDB_ARGS="--locale=C" -d -p5432:5432 orioledb/orioledb:latest-pg17` (medium confidence, run, README L104) **⚠ caution**
  - L102: ````bash`
  - L103: `# !Don't forget to set default locale to C, POSIX or use icu-locale`
  - L104: `docker run --name some-postgres -e POSTGRES_PASSWORD=... -e POSTGRES_INITDB_ARGS="--locale=C" -d -p5432:5432 orioledb/orioledb:latest-pg17`
  - L105: `````

- [ ] `git clone https://github.com/orioledb/orioledb` (high confidence, clone, README L122)
  - L120: `# 1. Clone this repo first -- .pgtags pins the exact patched-PostgreSQL`
  - L121: `# commit you must build against.`
  - L122: `$ git clone https://github.com/orioledb/orioledb`
  - L123: `$ cd orioledb`

- [ ] `git clone https://github.com/orioledb/postgres orioledb-postgres` (high confidence, clone, README L133)
  - L131: `# one -- it moves).`
  - L132: `$ cd ..`
  - L133: `$ git clone https://github.com/orioledb/postgres orioledb-postgres`
  - L134: `$ cd orioledb-postgres`


### Gentleman-Programming/gentle-ai

- Repo: <https://github.com/Gentleman-Programming/gentle-ai>
- Language: Go
- Commands: 2

- [ ] `brew install gentleman-programming/tap/gentle-ai` (medium confidence, install, README L280)
  - L278: ````bash`
  - L279: `# macOS (Homebrew)`
  - L280: `brew install gentleman-programming/tap/gentle-ai`
  - L281: ``

- [ ] `go install github.com/gentleman-programming/gentle-ai/v5/cmd/gentle-ai@v5.0.0` (medium confidence, install, README L286)
  - L284: ``
  - L285: `# Windows (PowerShell) — source install of v5.0.0, needs Go 1.25.10+`
  - L286: `go install github.com/gentleman-programming/gentle-ai/v5/cmd/gentle-ai@v5.0.0`
  - L287: `````


### affaan-m/ECC

- Repo: <https://github.com/affaan-m/ECC>
- Language: JavaScript
- Commands: 11

- [ ] `git clone https://github.com/affaan-m/ECC.git` (medium confidence, clone, README L304)
  - L302: ``
  - L303: ````bash`
  - L304: `git clone https://github.com/affaan-m/ECC.git`
  - L305: `cd ECC`

- [ ] `git clone https://github.com/affaan-m/ECC.git` (medium confidence, clone, README L369)
  - L367: ``
  - L368: ````bash`
  - L369: `git clone https://github.com/affaan-m/ECC.git`
  - L370: `cd ECC`

- [ ] `npm install` (medium confidence, install, README L371)
  - L369: `git clone https://github.com/affaan-m/ECC.git`
  - L370: `cd ECC`
  - L371: `npm install`
  - L372: `bash scripts/sync-ecc-to-codex.sh`

- [ ] `git clone https://github.com/affaan-m/ECC.git` (medium confidence, clone, README L421)
  - L419: ``
  - L420: ````bash`
  - L421: `git clone https://github.com/affaan-m/ECC.git`
  - L422: `cd ECC`

- [ ] `git clone https://github.com/affaan-m/ECC.git` (medium confidence, clone, README L566)
  - L564: ``
  - L565: ````bash`
  - L566: `git clone https://github.com/affaan-m/ECC.git`
  - L567: `cd ECC`

- [ ] `git clone https://github.com/affaan-m/ECC.git` (medium confidence, clone, README L574)
  - L572: ``
  - L573: ````powershell`
  - L574: `git clone https://github.com/affaan-m/ECC.git`
  - L575: `cd ECC`

- [ ] `npm install -g ecc-universal@2.2.3` (medium confidence, install, README L1273)
  - L1271: ``
  - L1272: ````bash`
  - L1273: `npm install -g ecc-universal@2.2.3`
  - L1274: `ecc memory init --scope project`

- [ ] `npm install && bash scripts/sync-ecc-to-codex.sh` (medium confidence, install, README L1573)
  - L1571: ````bash`
  - L1572: `# Compatibility-only managed sync into ~/.codex`
  - L1573: `npm install && bash scripts/sync-ecc-to-codex.sh`
  - L1574: ``

- [ ] `npm install ecc-universal@2.2.3` (high confidence, install, README L1685)
  - L1683: `**Option 2: Install as npm package**`
  - L1684: ````bash`
  - L1685: `npm install ecc-universal@2.2.3`
  - L1686: `````

- [ ] `git clone https://github.com/affaan-m/ECC.git && cd ECC` (medium confidence, clone, README L1746)
  - L1744: ``
  - L1745: ````bash`
  - L1746: `git clone https://github.com/affaan-m/ECC.git && cd ECC`
  - L1747: `copilot skill list`

- [ ] `git clone --depth 1 https://github.com/affaan-m/ECC.git && cd ECC` (medium confidence, clone, README L1760)
  - L1758: ``
  - L1759: ````bash`
  - L1760: `git clone --depth 1 https://github.com/affaan-m/ECC.git && cd ECC`
  - L1761: `npx -y @github/copilot@1.0.82 skill list --json | jq '[.[] | select(.source=="project")] | length'`


### langbot-app/LangBot

- Repo: <https://github.com/langbot-app/LangBot>
- Language: Python
- Commands: 1

- [ ] `git clone https://github.com/langbot-app/LangBot` (medium confidence, clone, README L93)
  - L91: ``
  - L92: ````bash`
  - L93: `git clone https://github.com/langbot-app/LangBot`
  - L94: `cd LangBot/docker`


### linshenkx/prompt-optimizer

- Repo: <https://github.com/linshenkx/prompt-optimizer>
- Language: TypeScript
- Commands: 5

- [ ] `docker run -d -p 8081:80 --restart unless-stopped --name prompt-optimizer linshen/prompt-optimizer` (medium confidence, run, README L142)
  - L140: ````bash`
  - L141: `# Run container (default configuration)`
  - L142: `docker run -d -p 8081:80 --restart unless-stopped --name prompt-optimizer linshen/prompt-optimizer`
  - L143: ``

- [ ] `git clone https://github.com/linshenkx/prompt-optimizer.git` (medium confidence, clone, README L161)
  - L159: ````bash`
  - L160: `# 1. Clone the repository`
  - L161: `git clone https://github.com/linshenkx/prompt-optimizer.git`
  - L162: `cd prompt-optimizer`

- [ ] `docker run -d -p 8081:80 -e VITE_OPENAI_API_KEY=your-openai-key -e MCP_DEFAULT_MODEL_PROVIDER=openai --name prompt-optimizer linshen/prompt-optimizer` (medium confidence, run, README L202) **⚠ caution**
  - L200: `For example, if you map the container's port 80 to port 8081 on the host:`
  - L201: ````bash`
  - L202: `docker run -d -p 8081:80 \`
  - L203: `-e VITE_OPENAI_API_KEY=your-openai-key \`

- [ ] `git clone https://github.com/linshenkx/prompt-optimizer.git` (medium confidence, clone, README L264)
  - L262: ````bash`
  - L263: `# 1. Clone the project`
  - L264: `git clone https://github.com/linshenkx/prompt-optimizer.git`
  - L265: `cd prompt-optimizer`

- [ ] `pnpm install` (medium confidence, install, README L268)
  - L266: ``
  - L267: `# 2. Install dependencies`
  - L268: `pnpm install`
  - L269: ``


### dicedb/dicedb

- Repo: <https://github.com/dicedb/dicedb>
- Language: C
- Commands: 2

- [ ] `docker run --name dicedb-001 -p 6379:6379 -v $(pwd)/data:/data/ dicedb/dicedb` (medium confidence, run, README L17)
  - L15: ``
  - L16: ````bash`
  - L17: `docker run \`
  - L18: `--name dicedb-001 \`

- [ ] `docker run --name dicedb-001 -p 6379:6379 -v $(pwd)/data:/data/ dicedb/dicedb dicedb-server --port 6379 --maxmemory 500mb --protected-mode no` (medium confidence, run, README L30)
  - L28: ``
  - L29: ````bash`
  - L30: `docker run \`
  - L31: `--name dicedb-001 \`


### mvanhorn/cli-printing-press

- Repo: <https://github.com/mvanhorn/cli-printing-press>
- Language: Go
- Commands: 3

- [ ] `go install github.com/mvanhorn/cli-printing-press/v4/cmd/cli-printing-press@latest` (high confidence, install, README L70)
  - L68: ``
  - L69: ````bash`
  - L70: `go install github.com/mvanhorn/cli-printing-press/v4/cmd/cli-printing-press@latest`
  - L71: `````

- [ ] `git clone https://github.com/mvanhorn/cli-printing-press.git` (high confidence, clone, README L104)
  - L102: ``
  - L103: ````bash`
  - L104: `git clone https://github.com/mvanhorn/cli-printing-press.git`
  - L105: `cd cli-printing-press`

- [ ] `brew install lefthook` (medium confidence, install, README L576)
  - L574: ``
  - L575: ````bash`
  - L576: `brew install lefthook`
  - L577: `lefthook install --reset-hooks-path`


### mdiri-ai/SoduWork

- Repo: <https://github.com/mdiri-ai/SoduWork>
- Language: JavaScript
- Commands: 1

- [ ] `git clone https://github.com/mdiri-ai/SoduWork` (medium confidence, clone, README L28)
  - L26: ``
  - L27: ````sh`
  - L28: `git clone https://github.com/mdiri-ai/SoduWork`
  - L29: `cd SoduWork`


### Future-House/paper-qa

- Repo: <https://github.com/Future-House/paper-qa>
- Language: Python
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


### DayuanJiang/next-ai-draw-io

- Repo: <https://github.com/DayuanJiang/next-ai-draw-io>
- Language: TypeScript
- Commands: 2

- [ ] `git clone https://github.com/DayuanJiang/next-ai-draw-io` (high confidence, clone, README L154)
  - L152: ``
  - L153: ````bash`
  - L154: `git clone https://github.com/DayuanJiang/next-ai-draw-io`
  - L155: `cd next-ai-draw-io`

- [ ] `npm install` (high confidence, install, README L156)
  - L154: `git clone https://github.com/DayuanJiang/next-ai-draw-io`
  - L155: `cd next-ai-draw-io`
  - L156: `npm install`
  - L157: `cp env.example .env.local   # add your provider and API key, see "Models and providers" below`


### Tencent/LoopForge

- Repo: <https://github.com/Tencent/LoopForge>
- Language: Go
- Commands: 1

- [ ] `git clone https://github.com/Tencent/LoopForge.git` (high confidence, clone, README L76)
  - L74: ``
  - L75: ````bash`
  - L76: `git clone https://github.com/Tencent/LoopForge.git`
  - L77: `cd LoopForge`


### chatchat-space/Langchain-Chatchat

- Repo: <https://github.com/chatchat-space/Langchain-Chatchat>
- Language: Python
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


### iOfficeAI/AionUi

- Repo: <https://github.com/iOfficeAI/AionUi>
- Language: TypeScript
- Commands: 1

- [ ] `brew install aionui` (high confidence, install, README L645) **⚠ caution**
  - L643: ````bash`
  - L644: `# Alternatively, macOS via Homebrew`
  - L645: `brew install aionui`
  - L646: `````


### BaaRai/ARTEX

- Repo: <https://github.com/BaaRai/ARTEX>
- Language: Go
- Commands: 9

- [ ] `git clone https://github.com/BaaRai/ARTEX.git` (high confidence, clone, README L49)
  - L47: ``
  - L48: ````bash`
  - L49: `git clone https://github.com/BaaRai/ARTEX.git`
  - L50: `cd ARTEX`

- [ ] `docker compose up -d --build` (high confidence, run, README L52)
  - L50: `cd ARTEX`
  - L51: `cp .env.example .env            # set POSTGRES_PASSWORD (and optionally an LLM key)`
  - L52: `docker compose up -d --build    # builds from this checkout, starts PostgreSQL`
  - L53: `````

- [ ] `git clone https://github.com/BaaRai/ARTEX.git` (high confidence, clone, README L322)
  - L320: ``
  - L321: ````bash`
  - L322: `git clone https://github.com/BaaRai/ARTEX.git`
  - L323: `cd ARTEX`

- [ ] `git clone https://github.com/BaaRai/ARTEX.git` (high confidence, clone, README L343)
  - L341: ``
  - L342: ````bash`
  - L343: `git clone https://github.com/BaaRai/ARTEX.git`
  - L344: `cd ARTEX`

- [ ] `docker compose up -d --build` (high confidence, run, README L346)
  - L344: `cd ARTEX`
  - L345: `cp .env.example .env            # set POSTGRES_PASSWORD, optionally ANTHROPIC_API_KEY`
  - L346: `docker compose up -d --build`
  - L347: `# → http://localhost:8787`

- [ ] `docker pull ghcr.io/baarai/artex:latest` (high confidence, install, README L372)
  - L370: ``
  - L371: ````bash`
  - L372: `docker pull ghcr.io/baarai/artex:latest`
  - L373: ``

- [ ] `docker run -d --name artex --security-opt no-new-privileges:true -p 127.0.0.1:8787:8787 -p 127.0.0.1:8788:8788 -e ARTEX_PG_HOST=host.docker.internal -e ARTEX_PG_PORT=5432 -e ARTEX_PG_USER=artex -e ARTEX_PG_PASSWORD='yourpass' -e ARTEX_PG_DBNAME=artex -e ARTEX_PG_SSLMODE=disable -e ARTEX_JWT_KEY_DIR=/app/keys -v "$PWD/data:/app/data" -v "$PWD/keys:/app/keys" ghcr.io/baarai/artex:latest` (high confidence, run, README L375)
  - L373: ``
  - L374: `mkdir -p data keys`
  - L375: `docker run -d --name artex \`
  - L376: `--security-opt no-new-privileges:true \`

- [ ] `docker compose build artex` (medium confidence, build, README L838)
  - L836: `cd ARTEX`
  - L837: `git pull`
  - L838: `docker compose build artex`
  - L839: `docker compose up -d artex`

- [ ] `docker compose up -d artex` (medium confidence, run, README L839)
  - L837: `git pull`
  - L838: `docker compose build artex`
  - L839: `docker compose up -d artex`
  - L840: `docker image prune -f            # optional`


### eosphoros-ai/DB-GPT

- Repo: <https://github.com/eosphoros-ai/DB-GPT>
- Language: Python
- Commands: 1

- [ ] `pip install dbgpt-app` (medium confidence, install, README L202)
  - L200: ``
  - L201: ````bash`
  - L202: `pip install dbgpt-app`
  - L203: `dbgpt start`


### can1357/oh-my-pi

- Repo: <https://github.com/can1357/oh-my-pi>
- Language: TypeScript
- Commands: 2

- [ ] `brew install can1357/tap/omp` (high confidence, install, README L54)
  - L52: ``
  - L53: ````sh`
  - L54: `brew install can1357/tap/omp`
  - L55: `````

- [ ] `bun install -g @oh-my-pi/pi-coding-agent` (high confidence, install, README L60)
  - L58: ``
  - L59: ````sh`
  - L60: `bun install -g @oh-my-pi/pi-coding-agent`
  - L61: `````


### mem0ai/mem0

- Repo: <https://github.com/mem0ai/mem0>
- Language: Python
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


### paperclipai/paperclip

- Repo: <https://github.com/paperclipai/paperclip>
- Language: TypeScript
- Commands: 2

- [ ] `git clone https://github.com/paperclipai/paperclip.git` (high confidence, clone, README L414)
  - L412: ``
  - L413: ````bash`
  - L414: `git clone https://github.com/paperclipai/paperclip.git`
  - L415: `cd paperclip`

- [ ] `pnpm install` (high confidence, install, README L416)
  - L414: `git clone https://github.com/paperclipai/paperclip.git`
  - L415: `cd paperclip`
  - L416: `pnpm install`
  - L417: `pnpm dev`

---

## Sign-off

- Reviewed by: ______________________  Date: ____________
- Repos reviewed: ______ / 50
- Commands judged correct: ______ / 158
- False positives / notes:
  - 
