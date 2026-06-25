"""
InSynBio ADC Intelligent Design Module
=======================================
Provides rule-based + data-driven recommendation for ADC component selection.

Public API
----------
    ADCDesignEngine  — main entry point for generating design proposals
    ADCDesignReport  — renders proposals into structured Markdown / JSON reports
"""
from .adc_decision_engine import ADCDesignEngine  # noqa: F401
