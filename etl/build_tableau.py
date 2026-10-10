"""Build a Tableau workbook against extracts/tableau_public_pack.xlsx.

Tableau Public cannot live-query Snowflake. This workbook is the publish file:
open it in Tableau Public Desktop, then publish to the maf345 profile.
"""
from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

import pandas as pd

from etl.config import ROOT

# Numeric fields that must stay dimensions (discrete), not summed measures.
DIMENSIONS = {
    "YEAR",
    "MONTH",
    "QUARTER",
    "SALE_HOUR",
    "STORE_ID",
    "PRODUCT_ID",
    "PRODUCT_A",
    "PRODUCT_B",
    "CUSTOMER_ID",
    "ISO_WEEK",
    "DOW_ISO",
    "DAY_OF_MONTH",
}

SHEETS = [
    ("store_perf", "Store revenue", "STORE_NAME", "REVENUE", "Bar"),
    ("product_total", "Product revenue", "PRODUCT_NAME", "REVENUE", "Bar"),
    ("monthly_growth", "Monthly revenue", "PERIOD", "REVENUE", "Bar"),
    ("member_guest", "Member vs guest", "CUSTOMER_TYPE", "REVENUE", "Bar"),
    ("payment", "Payment mix", "PAYMENT_TYPE", "REVENUE", "Bar"),
    ("discount_band", "Discount bands", "DISCOUNT_BAND", "REVENUE", "Bar"),
    ("hourly", "Hour of day", "SALE_HOUR", "TXN_COUNT", "Bar"),
    ("feed_monthly", "Feed coverage", "MONTH", "ITEM_COVERAGE_PCT", "Line"),
    ("market_basket", "Basket lift", "PRODUCT_A_NAME", "LIFT", "Bar"),
    ("rfm_summary", "Member churn", "CHURN_FLAG", "CUSTOMERS", "Bar"),
    ("kpi", "Executive KPI", None, None, "Automatic"),
]


def build_workbook(extract_paths: list[Path]) -> Path:
    xlsx = next(p for p in extract_paths if p.suffix.lower() == ".xlsx")
    book = pd.ExcelFile(xlsx)
    frames = {name: pd.read_excel(book, name) for name in book.sheet_names}
    out_dir = ROOT / "tableau"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "Retail_Sales_Analysis.twb"
    path.write_text(_workbook_xml(frames, xlsx.resolve()), encoding="utf-8")
    return path


def _workbook_xml(frames: dict[str, pd.DataFrame], xlsx: Path) -> str:
    filename = escape(str(xlsx).replace("\\", "/"))
    datasources = []
    worksheets = []
    windows = []
    for sheet, title, row_field, col_field, mark in SHEETS:
        if sheet not in frames:
            continue
        ds_name = f"excel-direct.{sheet}"
        datasources.append(_datasource(ds_name, sheet, frames[sheet], filename))
        worksheets.append(_worksheet(ds_name, title, frames[sheet], row_field, col_field, mark))
        windows.append(_window(title))
    dashboard = _dashboard()
    windows.append(
        """
    <window class='dashboard' name='Interview pack'>
      <viewpoints>
        <viewpoint name='Store revenue' />
        <viewpoint name='Product revenue' />
        <viewpoint name='Member vs guest' />
        <viewpoint name='Feed coverage' />
      </viewpoints>
    </window>"""
    )
    return f"""<?xml version='1.0' encoding='utf-8' ?>
<workbook source-build='2022.3.0 (20223.22.1011.2312)' source-platform='win' version='18.1' xmlns:user='http://www.tableausoftware.com/xml/user'>
  <preferences>
    <preference name='ui.encoding.shelf.size' value='24' />
  </preferences>
  <datasources>
    {''.join(datasources)}
  </datasources>
  <worksheets>
    {''.join(worksheets)}
  </worksheets>
  <dashboards>
    {dashboard}
  </dashboards>
  <windows source-height='30'>
    {''.join(windows)}
  </windows>
</workbook>
"""


def _datasource(ds_name: str, sheet: str, frame: pd.DataFrame, filename: str) -> str:
    columns_xml = []
    meta = []
    declarations = []
    for ordinal, col in enumerate(frame.columns):
        kind = _kind(col, frame[col])
        columns_xml.append(
            f"<column datatype='{kind['datatype']}' name='{escape(str(col))}' ordinal='{ordinal}' />"
        )
        meta.append(
            f"""
          <metadata-record class='column'>
            <remote-name>{escape(str(col))}</remote-name>
            <remote-type>{kind['remote_type']}</remote-type>
            <local-name>[{escape(str(col))}]</local-name>
            <parent-name>[{sheet}$]</parent-name>
            <remote-alias>{escape(str(col))}</remote-alias>
            <ordinal>{ordinal}</ordinal>
            <local-type>{kind['datatype']}</local-type>
            <aggregation>{kind['aggregation']}</aggregation>
            <contains-null>true</contains-null>
            <object-id>[{sheet}$]</object-id>
          </metadata-record>"""
        )
        declarations.append(
            f"<column datatype='{kind['datatype']}' name='[{escape(str(col))}]' role='{kind['role']}' type='{kind['semantic']}' />"
        )
    cols = "".join(columns_xml)
    return f"""
    <datasource caption='{sheet}' inline='true' name='{ds_name}' version='18.1'>
      <connection class='excel-direct' cleaning='no' compat='no' filename='{filename}' interpretationMode='0' password='' server='' validate='no'>
        <relation name='{sheet}' table='[{sheet}$]' type='table'>
          <columns>
            {cols}
          </columns>
        </relation>
        <metadata-records>
          {''.join(meta)}
          <metadata-record class='capability'>
            <remote-name />
            <remote-type>0</remote-type>
            <parent-name>[{sheet}$]</parent-name>
            <remote-alias />
            <aggregation>Count</aggregation>
            <contains-null>true</contains-null>
            <attributes>
              <attribute datatype='integer' name='context'>0</attribute>
              <attribute datatype='boolean' name='header'>true</attribute>
              <attribute datatype='integer' name='outcome'>6</attribute>
            </attributes>
          </metadata-record>
        </metadata-records>
      </connection>
      <aliases enabled='yes' />
      {''.join(declarations)}
      <layout dim-ordering='alphabetic' measure-ordering='alphabetic' show-structure='true' />
    </datasource>"""


def _kind(name: str, series: pd.Series) -> dict:
    if pd.api.types.is_datetime64_any_dtype(series):
        return {
            "datatype": "datetime",
            "remote_type": "135",
            "aggregation": "Year",
            "role": "dimension",
            "semantic": "ordinal",
        }
    numeric = pd.api.types.is_numeric_dtype(series)
    if numeric and str(name) not in DIMENSIONS:
        return {
            "datatype": "real",
            "remote_type": "5",
            "aggregation": "Sum",
            "role": "measure",
            "semantic": "quantitative",
        }
    if numeric:
        return {
            "datatype": "integer",
            "remote_type": "20",
            "aggregation": "Count",
            "role": "dimension",
            "semantic": "ordinal",
        }
    return {
        "datatype": "string",
        "remote_type": "130",
        "aggregation": "Count",
        "role": "dimension",
        "semantic": "nominal",
    }


def _worksheet(ds_name: str, title: str, frame: pd.DataFrame, row_field, col_field, mark: str) -> str:
    deps = []
    for col in frame.columns:
        kind = _kind(col, frame[col])
        deps.append(
            f"<column datatype='{kind['datatype']}' name='[{escape(str(col))}]' role='{kind['role']}' type='{kind['semantic']}' />"
        )
    if row_field and col_field:
        rows = _shelf(ds_name, row_field, frame)
        cols = _shelf(ds_name, col_field, frame)
    else:
        # One-row KPI: list every measure on rows so the sheet opens as a text table.
        rows = "".join(_shelf(ds_name, c, frame) for c in frame.columns if _kind(c, frame[c])["role"] == "measure")
        cols = ""
    return f"""
    <worksheet name='{escape(title)}'>
      <table>
        <view>
          <datasources>
            <datasource name='{ds_name}' />
          </datasources>
          <datasource-dependencies datasource='{ds_name}'>
            {''.join(deps)}
          </datasource-dependencies>
          <aggregation value='true' />
        </view>
        <style />
        <panes>
          <pane>
            <view>
              <breakdown value='auto' />
            </view>
            <mark class='{mark}' />
          </pane>
        </panes>
        <rows>{rows}</rows>
        <cols>{cols}</cols>
      </table>
    </worksheet>"""


def _shelf(ds_name: str, field: str, frame: pd.DataFrame) -> str:
    kind = _kind(field, frame[field])
    if kind["role"] == "measure":
        token = "sum" if kind["aggregation"] == "Sum" else "count"
        suffix = "qk"
    else:
        token = "none"
        suffix = "ok" if kind["semantic"] == "ordinal" else "nk"
    return f"[{ds_name}].[{token}:{field}:{suffix}]"


def _window(title: str) -> str:
    return f"""
    <window class='worksheet' name='{escape(title)}'>
      <cards>
        <edge name='left'>
          <strip size='160'>
            <card type='pages' />
            <card type='filters' />
            <card type='marks' />
          </strip>
        </edge>
        <edge name='top'>
          <strip size='31'>
            <card type='columns' />
          </strip>
          <strip size='31'>
            <card type='rows' />
          </strip>
        </edge>
      </cards>
    </window>"""


def _dashboard() -> str:
    return """
    <dashboard name='Interview pack'>
      <style />
      <size maxheight='800' maxwidth='1200' minheight='800' minwidth='1200' />
      <zones>
        <zone h='100000' id='2' type='layout-basic' w='100000' x='0' y='0'>
          <zone h='100000' id='3' param='vert' type='layout-flow' w='100000' x='0' y='0'>
            <zone h='25000' id='4' name='Store revenue' w='100000' x='0' y='0' />
            <zone h='25000' id='5' name='Product revenue' w='100000' x='0' y='25000' />
            <zone h='25000' id='6' name='Member vs guest' w='100000' x='0' y='50000' />
            <zone h='25000' id='7' name='Feed coverage' w='100000' x='0' y='75000' />
          </zone>
        </zone>
      </zones>
    </dashboard>"""
