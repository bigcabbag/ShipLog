# M1 面试问答卡：FastAPI + DeepSeek + LangChain

## 1. FastAPI 在这个项目里干什么？

把 AI 能力包装成 HTTP 接口。前端或其他服务通过 `POST /chat` 发 JSON，FastAPI 校验参数、调用 LangChain、返回 JSON。

类比：Express 路由 + Zod 校验。

## 2. `.env` 和 `python-dotenv` 干什么？

`.env` 存密钥和配置，不提交 Git。`load_dotenv()` 在启动时把变量加载到 `os.environ`，代码用 `os.getenv()` 读取。

## 3. 为什么用 `langchain-openai` 接 DeepSeek？

DeepSeek 提供 **OpenAI 兼容 API**。`ChatOpenAI` 只需改 `base_url` 和 `api_key`，不用写裸 HTTP 请求。

## 4. `SystemMessage` 和 `HumanMessage` 区别？

- `SystemMessage`：设定 AI 角色/规则（可选）
- `HumanMessage`：用户说的话

对应 Chat Completions API 里 `role: system` 和 `role: user`。

## 5. 为什么用 `async def` 和 `ainvoke`？

FastAPI 原生支持异步。`ainvoke` 在等待 DeepSeek 网络响应时不阻塞其他请求。

## 自检（能流利回答再进 M2）

- [ ] 请求从 `/chat` 进来到返回，经过哪几个文件？
- [ ] Token 计费发生在哪一步？（调用 DeepSeek API 时）
- [ ] 如果把模型换成通义，改哪几个环境变量？
