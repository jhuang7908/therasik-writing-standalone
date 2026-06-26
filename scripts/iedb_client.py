#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
iedb_client.py

 IEDB Tools API ：

- MHC-I binding:  https://tools-cluster-interface.iedb.org/tools_api/mhci/

- MHC-II binding: https://tools-cluster-interface.iedb.org/tools_api/mhcii/

：

-  v3 ""（Hybrid ）

-  IEDB recommended ； allele、

：

- ：requests
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Optional
import requests


IEDB_BASE = "https://tools-cluster-interface.iedb.org/tools_api"


class IEDBError(RuntimeError):
    """IEDB 。"""
    pass


@dataclass
class IEDBRequestConfig:
    method: str = "recommended"   #  mhci / mhcii 
    length: Optional[str] = None  # mhci: "8,9"; mhcii: "15" or "asis"
    species: Optional[str] = None #  mhci/processing ，mhcii 
    # ， email_address 


def _parse_tsv(text: str) -> List[Dict[str, str]]:
    """
     IEDB  TSV  list[dict]。
     header。
    """
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return []

    header = lines[0].split("\t")
    rows = []
    for ln in lines[1:]:
        cols = ln.split("\t")
        # ，
        if len(cols) != len(header):
            continue
        row = dict(zip(header, cols))
        rows.append(row)
    return rows


def _post_iedb(endpoint: str, data: Dict[str, str]) -> List[Dict[str, str]]:
    """
     POST ， list[dict]。
    """
    url = f"{IEDB_BASE}/{endpoint.strip('/')}/"
    try:
        resp = requests.post(url, data=data, timeout=120)
    except Exception as e:
        raise IEDBError(f"Request to IEDB failed: {e}") from e

    if resp.status_code != 200:
        raise IEDBError(
            f"IEDB returned non-200 status: {resp.status_code}\n"
            f"Text: {resp.text[:500]}"
        )

    return _parse_tsv(resp.text)


def predict_mhcii_binding(
    sequence: str,
    alleles: List[str],
    config: Optional[IEDBRequestConfig] = None,
) -> List[Dict[str, str]]:
    """
     IEDB MHC-II binding API。

    ：
    - sequence:  V （，）

    - alleles: HLA  ["HLA-DRB1*01:01", "HLA-DRB1*04:01"]

    - config.method:  "recommended"（NetMHCIIpan EL 4.1）

    - config.length:  "15"  "11,12,13,14,15"  "asis"
                      IEDB （ length=15）

    ：
    - list[dict]， IEDB ， IEDB ，
      ：allele, start, end, peptide, percent_rank, ic50 。
    """
    if config is None:
        config = IEDBRequestConfig()

    data = {
        "sequence_text": sequence,
        "method": config.method or "recommended",
        "allele": ",".join(alleles),
    }

    if config.length:
        data["length"] = config.length

    return _post_iedb("mhcii", data)


def predict_mhci_binding(
    sequence: str,
    alleles: List[str],
    config: Optional[IEDBRequestConfig] = None,
) -> List[Dict[str, str]]:
    """
     IEDB MHC-I binding API。

    ：
    - sequence: 

    - alleles: ["HLA-A*02:01", "HLA-B*07:02", ...]

    - config.length:  "8,9,10" 

    - config.species: ， "human"， API  allele （）

    ：
    - ，Class II ，。
    """
    if config is None:
        config = IEDBRequestConfig()

    data = {
        "sequence_text": sequence,
        "method": config.method or "recommended",
        "allele": ",".join(alleles),
    }

    if config.length:
        data["length"] = config.length
    if config.species:
        data["species"] = config.species

    return _post_iedb("mhci", data)























