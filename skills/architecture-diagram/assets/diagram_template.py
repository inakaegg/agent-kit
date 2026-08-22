"""構成図のテンプレート（mingrammer/diagrams、公式アイコン、単体で表示できる SVG）。

使い方:
  1. docs/diagrams/<name>.py へコピーし、NODES / EDGES の部分を書き換える
  2. uv run --with diagrams python docs/diagrams/<name>.py  （要 Graphviz）
  3. 出力 <name>.svg を README から <img src=...> で参照する

ノードは diagrams の既定（アイコンと文字が同じ固定サイズの箱）を使わず、Graphviz の HTML ラベルに
<IMG> を埋め込む。アイコン（ICON_PX）と文字（TITLE_PT / SUB_PT）を独立に決められ、ノード幅は
文字に合わせて自動で決まるため、文字を大きくしても隣と重ならない。
"""

import base64
import html
import re
from pathlib import Path

import diagrams
from diagrams import Cluster, Diagram, Edge
from diagrams.aws.compute import Lambda
from diagrams.aws.database import Dynamodb
from diagrams.aws.network import APIGateway
from diagrams.onprem.client import Users

HERE = Path(__file__).resolve().parent  # 出力先をスクリプトの場所に固定する
ICON_BASE = Path(diagrams.__file__).resolve().parent.parent  # diagrams 同梱アイコンの場所

FONT = "Hiragino Sans"  # 生成時のフォント（Graphviz が文字幅を測るのに使う）
# SVG の文字は閲覧側のフォントで描かれるので、複数 OS で日本語が出る候補を並べる
FONT_STACK = "Hiragino Sans, Noto Sans JP, Yu Gothic UI, Meiryo, sans-serif"
ICON_PX = 72  # アイコンの一辺（px、96dpi 基準）
TITLE_PT = 16  # ノード名
SUB_PT = 13  # 補足行
SUB_COLOR = "#5E6B64"
LATER_COLOR = "#8E9A94"  # 後回し・将来の群
ACCENT = "#1F7A6E"  # 強調したい経路（課金、危険など）は 1 色だけ

GRAPH = {"fontname": FONT, "fontsize": "15", "pad": "0.4", "nodesep": "0.35", "ranksep": "0.7", "splines": "spline"}
NODE = {"fontname": FONT}
EDGE = {"fontname": FONT, "fontsize": "13"}
CLUSTER = {"fontname": FONT, "fontsize": "15"}
LATER_CLUSTER = {**CLUSTER, "style": "dashed", "color": LATER_COLOR, "fontcolor": LATER_COLOR}


def svc(cls, title, *sub, color="#1C2420", sub_color=SUB_COLOR):
    """アイコン + タイトル + 補足行のノード。幅は文字に合わせて自動で決まる。"""
    icon = ICON_BASE / cls._icon_dir / cls._icon
    rows = [
        f'<TR><TD FIXEDSIZE="TRUE" WIDTH="{ICON_PX}" HEIGHT="{ICON_PX}"><IMG SCALE="TRUE" SRC="{icon}"/></TD></TR>',
        f'<TR><TD><FONT POINT-SIZE="{TITLE_PT}" COLOR="{color}">{html.escape(title)}</FONT></TD></TR>',
    ]
    rows += [f'<TR><TD><FONT POINT-SIZE="{SUB_PT}" COLOR="{sub_color}">{html.escape(s)}</FONT></TD></TR>' for s in sub]
    label = '<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="1">' + "".join(rows) + "</TABLE>>"
    return cls(label, image="", fixedsize="false", width="0", height="0", margin="0")


def later(cls, title, *sub):
    """後回し・将来の要素（灰色）。"""
    return svc(cls, title, *sub, color=LATER_COLOR, sub_color=LATER_COLOR)


def finalize_svg(path: Path) -> None:
    """Graphviz の SVG はアイコンをローカルパスで参照するので、base64 で埋め込んで単体で表示できる形にする。"""
    svg = path.read_text()

    def embed(m):
        data = base64.b64encode(Path(m.group(1)).read_bytes()).decode()
        return f'xlink:href="data:image/png;base64,{data}"'

    svg = re.sub(r'xlink:href="(/[^"]+\.png)"', embed, svg)
    svg = svg.replace(f'font-family="{FONT}"', f'font-family="{FONT_STACK}"')
    svg = svg.replace('font-family="Sans-Serif"', f'font-family="{FONT_STACK}"')  # diagrams が図のタイトルに付ける既定
    path.write_text(svg)


# ---- ここから書き換える ---------------------------------------------------------------

with Diagram(
    "サービス構成（番号は実装の順序）",
    filename=str(HERE / "architecture"),
    outformat="svg",
    show=False,
    direction="TB",  # 構成図は TB、経路図は LR から始める
    graph_attr=GRAPH,
    node_attr=NODE,
    edge_attr=EDGE,
):
    with Cluster("手元", graph_attr=CLUSTER):
        user = svc(Users, "利用者", "ブラウザ")

    with Cluster("AWS  ap-northeast-1", graph_attr=CLUSTER):
        api = svc(APIGateway, "API Gateway ①", "HTTP API")
        fn = svc(Lambda, "Lambda ①", "Hono")
        ddb = svc(Dynamodb, "DynamoDB ①", "1 テーブル")

    with Cluster("後回し", graph_attr=LATER_CLUSTER):
        queue = later(Lambda, "非同期処理")

    user >> Edge(label="API を呼ぶ") >> api >> fn
    fn >> Edge(label="Query / Put", color=ACCENT, fontcolor=ACCENT, penwidth="2") >> ddb
    ddb >> Edge(style="invis") >> queue  # 後回しの群を最下段に固定する

finalize_svg(HERE / "architecture.svg")
