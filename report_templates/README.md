# Report Templates

， `scripts/report_cli.py dual`。

## Files
- `dual_report_source_template.md`: 
- `vhvl_humanization_dual_report_template.md`: VH/VL humanization 
- `vhh_humanization_dual_report_template.md`: VHH humanization 
- `vhh_cmc_dual_report_template.md`: VHH CMC 
- `vam_dual_report_template.md`: Virtual Affinity Maturation 
- `hapten_vam_dual_report_template.md`: Hapten VAM 
- `bispecific_cmc_dual_report_template.md`: Bispecific CMC 
- `adc_design_dual_report_template.md`: ADC design 
- `car_design_dual_report_template.md`: CAR design 
- `vaccine_design_dual_report_template.md`: Vaccine design 
- `epidesign_dual_report_template.md`: EpiDesignCore 
- `structure_run_dual_report_template.md`:  / docking 

## Usage
```bash
python scripts/report_cli.py dual "report_templates/vam_dual_report_template.md" --outdir "reports"
```

## Notes
-  `internal` 
- `<!-- INTERNAL_ONLY_START -->`  `<!-- INTERNAL_ONLY_END -->` 
-  `report_cli.py dual` 
-  `core/reporting/spec.py`
