"""


config.yaml，
"""

from __future__ import annotations

import os
import sys
import yaml
from pathlib import Path
from typing import Any, Dict, Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    # 
    pass

from dataclasses import dataclass, field


# （）
_PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass
class PathsConfig:
    """"""
    project_root: Path = field(default_factory=lambda: _PROJECT_ROOT)
    data_root: Path = field(default_factory=lambda: _PROJECT_ROOT / "data" / "germlines")
    output_root: Path = field(default_factory=lambda: _PROJECT_ROOT / "output")
    
    # VHH
    alpaca_dir: Path = field(default=None)
    alpaca_fasta: Path = field(default=None)
    alpaca_label: Path = field(default=None)
    alpaca_numbered: Path = field(default=None)
    alpaca_scaffolds: Path = field(default=None)
    
    # VH3
    human_dir: Path = field(default=None)
    human_fasta: Path = field(default=None)
    human_numbered: Path = field(default=None)
    human_scaffolds: Path = field(default=None)
    human_templates: Path = field(default=None)
    alignment_file: Path = field(default=None)
    
    # 
    fc_aa_dir: Path = field(default=None)
    imgt_dir: Path = field(default=None)
    benchmark_dir: Path = field(default=None)
    benchmark_gold_standard: Path = field(default=None)
    
    def __post_init__(self):
        """"""
        # project_root，Path
        if isinstance(self.project_root, str):
            self.project_root = Path(self.project_root) if self.project_root else _PROJECT_ROOT
        elif self.project_root is None:
            self.project_root = _PROJECT_ROOT
        
        # data_root
        if isinstance(self.data_root, str):
            self.data_root = self._resolve_path(self.data_root, {"project_root": self.project_root})
        elif self.data_root is None:
            self.data_root = self.project_root / "data" / "germlines"
        
        # output_root
        if isinstance(self.output_root, str):
            self.output_root = self._resolve_path(self.output_root, {"project_root": self.project_root})
        elif self.output_root is None:
            self.output_root = self.project_root / "output"
        
        # 
        context = {
            "project_root": self.project_root,
            "data_root": self.data_root,
            "output_root": self.output_root,
        }
        
        if self.alpaca_dir is None or isinstance(self.alpaca_dir, str):
            self.alpaca_dir = self._resolve_path(
                self.alpaca_dir or "{data_root}/vicugna_pacos_ig_aa",
                context
            )
        
        if self.alpaca_fasta is None or isinstance(self.alpaca_fasta, str):
            self.alpaca_fasta = self._resolve_path(
                self.alpaca_fasta or "{alpaca_dir}/IGHV_aa.fasta",
                {"alpaca_dir": self.alpaca_dir, **context}
            )
        
        if self.alpaca_label is None or isinstance(self.alpaca_label, str):
            self.alpaca_label = self._resolve_path(
                self.alpaca_label or "{alpaca_dir}/alpaca_ighv_vhh_label.tsv",
                {"alpaca_dir": self.alpaca_dir, **context}
            )
        
        if self.alpaca_numbered is None or isinstance(self.alpaca_numbered, str):
            self.alpaca_numbered = self._resolve_path(
                self.alpaca_numbered or "{alpaca_dir}/vhh_numbered/vhh_numbered_and_split.json",
                {"alpaca_dir": self.alpaca_dir, **context}
            )
        
        if self.alpaca_scaffolds is None or isinstance(self.alpaca_scaffolds, str):
            self.alpaca_scaffolds = self._resolve_path(
                self.alpaca_scaffolds or "{alpaca_dir}/vhh_scaffolds/vhh_scaffolds.json",
                {"alpaca_dir": self.alpaca_dir, **context}
            )
        
        if self.human_dir is None or isinstance(self.human_dir, str):
            self.human_dir = self._resolve_path(
                self.human_dir or "{data_root}/human_ig_aa",
                context
            )
        
        if self.human_fasta is None or isinstance(self.human_fasta, str):
            self.human_fasta = self._resolve_path(
                self.human_fasta or "{human_dir}/IGHV_aa.fasta",
                {"human_dir": self.human_dir, **context}
            )
        
        if self.human_numbered is None or isinstance(self.human_numbered, str):
            self.human_numbered = self._resolve_path(
                self.human_numbered or "{human_dir}/vh_numbered/human_vh_numbered_and_split.json",
                {"human_dir": self.human_dir, **context}
            )
        
        if self.human_scaffolds is None or isinstance(self.human_scaffolds, str):
            self.human_scaffolds = self._resolve_path(
                self.human_scaffolds or "{human_dir}/vh_scaffolds/human_vh3_scaffolds.json",
                {"human_dir": self.human_dir, **context}
            )
        
        if self.human_templates is None or isinstance(self.human_templates, str):
            self.human_templates = self._resolve_path(
                self.human_templates or "{human_dir}/vh_scaffolds/human_vh3_vhh_safe_templates.json",
                {"human_dir": self.human_dir, **context}
            )
        
        if self.alignment_file is None or isinstance(self.alignment_file, str):
            self.alignment_file = self._resolve_path(
                self.alignment_file or "{human_dir}/vh_scaffolds/human_vs_alpaca_scaffold_alignment.json",
                {"human_dir": self.human_dir, **context}
            )
        
        if self.fc_aa_dir is None or isinstance(self.fc_aa_dir, str):
            self.fc_aa_dir = self._resolve_path(
                self.fc_aa_dir or "{data_root}/fc_aa",
                context
            )
        
        if self.imgt_dir is None or isinstance(self.imgt_dir, str):
            self.imgt_dir = self._resolve_path(
                self.imgt_dir or "{data_root}/IMGT_V-/IMGT_V-QUEST_reference_directory",
                context
            )
        
        if self.benchmark_dir is None or isinstance(self.benchmark_dir, str):
            self.benchmark_dir = self._resolve_path(
                self.benchmark_dir or "{data_root}/benchmark",
                context
            )
        
        if self.benchmark_gold_standard is None or isinstance(self.benchmark_gold_standard, str):
            self.benchmark_gold_standard = self._resolve_path(
                self.benchmark_gold_standard or "{benchmark_dir}/gold_standard.json",
                {"benchmark_dir": self.benchmark_dir, **context}
            )
    
    @staticmethod
    def _resolve_path(path_str: str, context: Dict[str, Any]) -> Path:
        """，"""
        if not path_str:
            return Path(".")
        
        # 
        resolved = path_str
        for key, value in context.items():
            placeholder = f"{{{key}}}"
            if placeholder in resolved:
                if isinstance(value, Path):
                    resolved = resolved.replace(placeholder, str(value))
                else:
                    resolved = resolved.replace(placeholder, str(value))
        
        # ，project_root
        path = Path(resolved)
        if not path.is_absolute() and "project_root" in context:
            path = context["project_root"] / path
        
        return path.resolve() if path.exists() else path


@dataclass
class ScoringProfile:
    """Scoringprofile"""
    framework_identity: float = 0.5
    cdr_compatibility: float = 0.25
    developability: float = 0.25
    fr_immunogenicity: Optional[float] = None  # ，profile


@dataclass
class ScoringConfig:
    """Scoring"""
    active_profile: str = "default"
    profiles: Dict[str, ScoringProfile] = field(default_factory=lambda: {
        "default": ScoringProfile(
            framework_identity=0.5,
            cdr_compatibility=0.25,
            developability=0.25
        )
    })
    
    def get_active_weights(self) -> Dict[str, float]:
        """profile"""
        profile = self.profiles.get(self.active_profile, self.profiles["default"])
        weights = {
            "framework_identity": profile.framework_identity,
            "cdr_compatibility": profile.cdr_compatibility,
            "developability": profile.developability,
        }
        if profile.fr_immunogenicity is not None:
            weights["fr_immunogenicity"] = profile.fr_immunogenicity
        return weights


@dataclass
class CanonicalProxyConfig:
    """Canonical Proxy """
    enabled: bool = True
    agg_mode: str = "min"  # "min" | "mean"
    weight: float = 0.10  # 10% 
    floor_if_missing: float = 0.0


@dataclass
class ParametersConfig:
    """"""
    clustering_threshold: float = 0.90
    max_mutations: int = 5
    default_panel: str = "A"
    default_top_k: int = 3
    hard_min_cdr_score: float = 0.3
    soft_min_cdr_score: float = 0.5
    scoring: Optional[ScoringConfig] = None
    scoring_weights: Dict[str, float] = field(default_factory=lambda: {
        "framework_identity": 0.5,
        "cdr_compatibility": 0.25,
        "developability": 0.25,
    })  # 
    fallback_penalty_template: float = 0.8
    fallback_penalty_numbering: float = 0.9
    canonical_proxy: Optional[CanonicalProxyConfig] = None
    variant_ranking: Optional[dict] = None  #  config.yaml ，: {"canonical_proxy": {...}}
    extreme_cdr3_length: int = 20
    extreme_cdr3_cys_count: int = 3
    
    def get_scoring_weights(self) -> Dict[str, float]:
        """scoring（scoring profile，scoring_weights）"""
        if self.scoring:
            return self.scoring.get_active_weights()
        return self.scoring_weights


@dataclass
class AnarciiConfig:
    """ANARCII"""
    mode: str = "accuracy"
    cpu: bool = True
    batch_size: int = 32
    ncpu: int = -1
    verbose: bool = False


@dataclass
class DevelopabilityConfig:
    """Developability"""
    grade_a_threshold: float = 0.8
    grade_b_threshold: float = 0.6
    high_risk_liability_count: int = 2


@dataclass
class ImmunogenicityConfig:
    """Immunogenicity"""
    fr_hotspot_low: int = 2
    fr_hotspot_medium: int = 5
    fr_hotspot_high: int = 10


@dataclass
class ReportingConfig:
    """"""
    default_format: str = "markdown"
    output_dir: Optional[Path] = None
    html_template: Optional[str] = None


@dataclass
class ApiConfig:
    """API"""
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    cors_enabled: bool = True


@dataclass
class Config:
    """"""
    paths: PathsConfig = field(default_factory=PathsConfig)
    parameters: ParametersConfig = field(default_factory=ParametersConfig)
    anarcii: AnarciiConfig = field(default_factory=AnarciiConfig)
    developability: DevelopabilityConfig = field(default_factory=DevelopabilityConfig)
    immunogenicity: ImmunogenicityConfig = field(default_factory=ImmunogenicityConfig)
    reporting: ReportingConfig = field(default_factory=ReportingConfig)
    api: ApiConfig = field(default_factory=ApiConfig)
    
    @classmethod
    def load(cls, config_path: Optional[Path] = None, validate: bool = True) -> Config:
        """
        YAML
        
        Args:
            config_path: （None，）
            validate: （True）
        
        Returns:
            Config
        
        Raises:
            ValueError: 
        """
        if config_path is None:
            config_path = _PROJECT_ROOT / "config.yaml"
        
        config_dict: Dict[str, Any] = {}
        
        # YAML
        if config_path.exists():
            with open(config_path, encoding='utf-8') as f:
                config_dict = yaml.safe_load(f) or {}
        
        # 
        config_dict = cls._apply_env_overrides(config_dict)
        
        # 
        config = cls._from_dict(config_dict)
        
        # 
        if validate:
            errors = cls.validate(config)
            if errors:
                raise ValueError(
                    f"Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
                )
        
        return config
    
    @staticmethod
    def validate(cfg: 'Config') -> list:
        """
        ，
        
        Args:
            cfg: Config
        
        Returns:
            （，）
        """
        errors = []
        
        # 
        required_paths = [
            ('alpaca_scaffolds', cfg.paths.alpaca_scaffolds),
            ('human_templates', cfg.paths.human_templates),
        ]
        for name, path in required_paths:
            if not path.exists():
                errors.append(f"Required path does not exist: {name} = {path}")
        
        # 
        params = cfg.parameters
        if not 0 < params.clustering_threshold <= 1:
            errors.append(
                f"clustering_threshold must be in (0, 1], got {params.clustering_threshold}"
            )
        
        if params.hard_min_cdr_score > params.soft_min_cdr_score:
            errors.append(
                f"hard_min_cdr_score ({params.hard_min_cdr_score}) must be <= "
                f"soft_min_cdr_score ({params.soft_min_cdr_score})"
            )
        
        if params.extreme_cdr3_length < 0:
            errors.append(f"extreme_cdr3_length must be >= 0, got {params.extreme_cdr3_length}")
        
        if params.extreme_cdr3_cys_count < 0:
            errors.append(
                f"extreme_cdr3_cys_count must be >= 0, got {params.extreme_cdr3_cys_count}"
            )
        
        # fallback
        if not 0 < params.fallback_penalty_template <= 1:
            errors.append(
                f"fallback_penalty_template must be in (0, 1], "
                f"got {params.fallback_penalty_template}"
            )
        
        if not 0 < params.fallback_penalty_numbering <= 1:
            errors.append(
                f"fallback_penalty_numbering must be in (0, 1], "
                f"got {params.fallback_penalty_numbering}"
            )
        
        return errors
    
    @staticmethod
    def _apply_env_overrides(config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """"""
        for key, value in os.environ.items():
            if not key.startswith("VHH_"):
                continue
            
            #  VHH_<SECTION>_<KEY>
            parts = key[4:].split("_", 1)  # "VHH_"
            if len(parts) != 2:
                continue
            
            section, subkey = parts[0].lower(), parts[1].lower()
            
            # （__）
            keys = subkey.split("__")
            
            # 
            if section not in config_dict:
                config_dict[section] = {}
            
            current = config_dict[section]
            for k in keys[:-1]:
                if k not in current:
                    current[k] = {}
                current = current[k]
            
            # 
            final_key = keys[-1]
            if isinstance(value, str):
                # 
                if value.lower() in ("true", "yes", "1"):
                    value = True
                elif value.lower() in ("false", "no", "0"):
                    value = False
                else:
                    try:
                        if "." in value:
                            value = float(value)
                        else:
                            value = int(value)
                    except ValueError:
                        pass  # 
            
            current[final_key] = value
        
        return config_dict
    
    @classmethod
    def _from_dict(cls, config_dict: Dict[str, Any]) -> Config:
        """"""
        paths_dict = config_dict.get("paths", {})
        parameters_dict = config_dict.get("parameters", {})
        anarcii_dict = config_dict.get("anarcii", {})
        developability_dict = config_dict.get("developability", {})
        immunogenicity_dict = config_dict.get("immunogenicity", {})
        reporting_dict = config_dict.get("reporting", {})
        api_dict = config_dict.get("api", {})
        
        # scoring（parameters_dict）
        scoring_dict = parameters_dict.pop("scoring", None)
        scoring_config = None
        if scoring_dict:
            active_profile = scoring_dict.get("active_profile", "default")
            profiles_dict = scoring_dict.get("profiles", {})
            profiles = {}
            for name, profile_dict in profiles_dict.items():
                # 
                profile_data = {
                    "framework_identity": profile_dict.get("framework_identity", 0.5),
                    "cdr_compatibility": profile_dict.get("cdr_compatibility", 0.25),
                    "developability": profile_dict.get("developability", 0.25),
                }
                if "fr_immunogenicity" in profile_dict:
                    profile_data["fr_immunogenicity"] = profile_dict["fr_immunogenicity"]
                profiles[name] = ScoringProfile(**profile_data)
            scoring_config = ScoringConfig(active_profile=active_profile, profiles=profiles)
        
        # 
        paths = PathsConfig(**paths_dict)
        #  variant_ranking（）
        variant_ranking_dict = parameters_dict.pop("variant_ranking", None)
        parameters = ParametersConfig(**parameters_dict)
        # scoring（）
        if scoring_config:
            parameters.scoring = scoring_config
        #  variant_ranking（）
        if variant_ranking_dict:
            parameters.variant_ranking = variant_ranking_dict
        anarcii = AnarciiConfig(**anarcii_dict)
        developability = DevelopabilityConfig(**developability_dict)
        immunogenicity = ImmunogenicityConfig(**immunogenicity_dict)
        reporting = ReportingConfig(**reporting_dict)
        api = ApiConfig(**api_dict)
        
        # reporting.output_dir
        if reporting.output_dir is None or isinstance(reporting.output_dir, str):
            if isinstance(reporting.output_dir, str):
                reporting.output_dir = PathsConfig._resolve_path(
                    reporting.output_dir,
                    {"project_root": paths.project_root, "output_root": paths.output_root}
                )
            else:
                reporting.output_dir = paths.output_root / "reports"
        
        return cls(
            paths=paths,
            parameters=parameters,
            anarcii=anarcii,
            developability=developability,
            immunogenicity=immunogenicity,
            reporting=reporting,
            api=api,
        )


# （）
_CFG: Optional[Config] = None


def get_config() -> Config:
    """（）"""
    global _CFG
    if _CFG is None:
        _CFG = Config.load()
    return _CFG


# 
CFG = property(lambda self: get_config())

# ，
def _init_cfg():
    global CFG
    CFG = get_config()

_init_cfg()

