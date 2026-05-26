# 不买服务器 + 不用访客装 westlake：预计算演化图

GitHub 上的 westlake 是 **源代码**，不是在线算力。  
Streamlit Cloud **不能** 可靠地 `pip install westlake` 后给每个访客实时跑演化。

**可行方案：你在本机算一次 → 把 PNG 推到 GitHub → 访客在网页看图。**

---

## 第一步：本机安装 westlake（只你装一次）

```powershell
pip install torch
pip install -e "E:\大学\学术项目\Agent-ChemiVerse\westlake-tutorial\westlake"
```

或从 Gitee：

```powershell
pip install git+https://gitee.com/yqiuu/astro-westlake.git
```

---

## 第二步：生成图并写入仓库

```powershell
cd C:\Users\ROG\astrochem-agent

# 跑模拟 + 画图 + 更新目录（约 5～15 分钟）
python scripts/publish_plots_to_repo.py ^
  --id nitrogen-default ^
  --title "含氮分子演化" ^
  --species N2,NH3,HCN,H2CO ^
  --run
```

会生成：

- `data/plots/nitrogen-default/*.png`
- `data/simulation_catalog.json`

若已有 `res.pickle`，可去掉 `--run` 只重画图。

---

## 第三步：推到 GitHub

```powershell
git add data/plots data/simulation_catalog.json
git commit -m "Add precomputed westlake plots"
git push
```

Streamlit Cloud 会自动重新部署。

---

## 第四步：访客使用

打开 `https://xxx.streamlit.app` → **Westlake 演化图** → 下拉选场景 → 看图。

访客：**不装 westlake、不买服务器、不连你的电脑**。

---

## 多加几个场景

```powershell
python scripts/publish_plots_to_repo.py --id organic-default --species CO,CH3OH,CH3OCH3 --run
python scripts/publish_plots_to_repo.py --id cch-demo --species CCH,HCN,CO --run
git add data/plots data/simulation_catalog.json
git push
```

---

## 和「实时模拟」的区别

| | 预计算图（本文） | 模拟 API 服务器 |
|--|------------------|-----------------|
| 买服务器 | 否 | 是（或 24h 开机的电脑） |
| 访客自定义物种实时算 | 否 | 是 |
| 展示 westlake 真实输出 | 是 | 是 |
| 维护成本 | 偶尔本机重算并 push | 服务器常开 |

若以后需要访客 **任意物种实时出图**，只能加算力（服务器或长期开机的实验室机器）。
