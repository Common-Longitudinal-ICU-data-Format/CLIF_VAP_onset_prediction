import pandas as pd
import duckdb
from typing import Union

def find_intubation_times(
    vent: pd.DataFrame, 
    time_window: Union[int, float] = 1
) -> pd.DataFrame:
    """
    Identify intubation timepoints where all required ventilator parameters are present.
    
    Uses a sliding time window to find timepoints where invasive mechanical ventilation 
    (IMV) device, ventilator mode, FiO2, and PEEP settings are all documented within 
    the specified time range.
    
    Parameters
    ----------
    vent : pd.DataFrame
        Ventilator data containing columns:
        - encounter_block
        - recorded_dttm
        - device_category
        - mode_category
        - fio2_set
        - peep_set
    
    time_window : int or float, default=1
        Time window in hours to search for required parameters around each timepoint.
        Creates a window of ±time_window hours (total span = 2 * time_window).
    
    Returns
    -------
    pd.DataFrame
        DataFrame with columns:
        - encounter_block: Patient/encounter identifier
        - recorded_dttm: Timepoint where all intubation criteria are met
        
        Sorted by encounter_block and recorded_dttm. Only distinct timepoints returned.
    
    Notes
    -----
    A timepoint is considered a valid intubation time if within ±time_window hours:
    - At least one IMV device record exists
    - At least one ventilator mode is documented
    - At least one FiO2 setting is documented
    - At least one PEEP setting is documented
    """
    conn = duckdb.connect()
    conn.register('vent_data', vent)
    
    query = f"""
    WITH time_windows AS (
        SELECT 
            encounter_block,
            recorded_dttm,
            -- Check for IMV device within time window
            MAX(CASE WHEN device_category = 'IMV' THEN 1 ELSE 0 END) 
                OVER (
                    PARTITION BY encounter_block 
                    ORDER BY recorded_dttm 
                    RANGE BETWEEN INTERVAL '{time_window} hours' PRECEDING 
                             AND INTERVAL '{time_window} hours' FOLLOWING
                ) as has_imv_in_window,
            
            -- Check for ventilator mode within time window
            MAX(CASE WHEN mode_category IS NOT NULL THEN 1 ELSE 0 END) 
                OVER (
                    PARTITION BY encounter_block 
                    ORDER BY recorded_dttm 
                    RANGE BETWEEN INTERVAL '{time_window} hours' PRECEDING 
                             AND INTERVAL '{time_window} hours' FOLLOWING
                ) as has_mode_in_window,
            
            -- Check for FiO2 setting within time window
            MAX(CASE WHEN fio2_set IS NOT NULL THEN 1 ELSE 0 END) 
                OVER (
                    PARTITION BY encounter_block 
                    ORDER BY recorded_dttm 
                    RANGE BETWEEN INTERVAL '{time_window} hours' PRECEDING 
                             AND INTERVAL '{time_window} hours' FOLLOWING
                ) as has_fio2_in_window,
            
            -- Check for PEEP setting within time window
            MAX(CASE WHEN peep_set IS NOT NULL THEN 1 ELSE 0 END) 
                OVER (
                    PARTITION BY encounter_block 
                    ORDER BY recorded_dttm 
                    RANGE BETWEEN INTERVAL '{time_window} hours' PRECEDING 
                             AND INTERVAL '{time_window} hours' FOLLOWING
                ) as has_peep_in_window
        FROM vent_data
    )
    SELECT DISTINCT
        encounter_block,
        recorded_dttm
    FROM time_windows
    WHERE has_imv_in_window = 1 
        AND has_mode_in_window = 1 
        AND has_fio2_in_window = 1 
        AND has_peep_in_window = 1
    ORDER BY encounter_block, recorded_dttm
    """
    
    result = conn.execute(query).df()
    conn.close()
    
    return result