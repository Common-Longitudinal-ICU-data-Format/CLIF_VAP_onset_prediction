import pandas as pd

def stitch_icu_stays(
    adt_df: pd.DataFrame,
    gap_hours: float = 6
) -> pd.DataFrame:
    """
    Stitch together ICU stays that are within a specified time gap.
    
    Parameters:
    -----------
    adt_df : pd.DataFrame
        ADT dataframe containing location and timing information. Must contain columns:
        - patient_id
        - encounter_block
        - hospitalization_id
        - in_dttm
        - out_dttm
        - location_category
        - location_type
    hospitalization_ids : list, pd.Series, or np.ndarray
        List/array of hospitalization IDs to filter
    gap_hours : float, default=6
        Maximum gap in hours between ICU stays to consider them linked
        
    Returns:
    --------
    pd.DataFrame
        DataFrame with stitched ICU stays, including columns:
        - encounter_block
        - icu_group
        - icu_rank
        - in_dttm
        - out_dttm
        - location_type
    """
    
    # Step 1: Filter for ICU/stepdown locations in cohort
    icu_mask = adt_df['location_category'].str.lower().isin(['icu', 'stepdown'])
    icu_adt_df = adt_df[icu_mask].copy()
    
    # Step 2: Initial ICU ranking
    icu_adt = icu_adt_df.sort_values(by=['encounter_block', 'in_dttm'])
    icu_adt['icu_rank'] = icu_adt.groupby(['encounter_block', 'in_dttm']).ngroup() + 1
    icu_adt['icu_rank'] = (
        icu_adt.groupby('encounter_block')['icu_rank']
        .rank(method='dense')
        .astype(int)
    )
    
    # Step 3: Prepare ICU block data
    icu_block = icu_adt.copy()
    icu_block = icu_block.drop_duplicates()
    icu_block = icu_block.sort_values(
        by=["encounter_block", "icu_rank"]
    ).reset_index(drop=True)
    
    # Step 4: Calculate time gap between consecutive ICU stays
    icu_block["next_in_dttm"] = icu_block.groupby("encounter_block")["in_dttm"].shift(-1)
    icu_block["out_to_next_icu_hrs"] = (
        (icu_block["next_in_dttm"] - icu_block["out_dttm"]).dt.total_seconds() / 3600
    )
    
    # Step 5: Create ICU groups based on time gap
    icu_block["linked6hrs"] = icu_block["out_to_next_icu_hrs"] < gap_hours
    icu_block = icu_block.sort_values(
        by=["encounter_block", "icu_rank"]
    ).reset_index(drop=True)
    
    # Initialize and update ICU groups
    icu_block['icu_group'] = icu_block.index + 1
    icu_block['icu_group'] = (
        icu_block.groupby('encounter_block')['icu_group']
        .transform(lambda group: group.where(
            ~icu_block.loc[group.index, 'linked6hrs']
        ).bfill().ffill())
    )
    
    # Aggregate by ICU group
    icu_block2 = icu_block.groupby(['encounter_block', 'icu_group']).agg(
        in_dttm=pd.NamedAgg(column='in_dttm', aggfunc='min'),
        out_dttm=pd.NamedAgg(column='out_dttm', aggfunc='max'),
        location_type=pd.NamedAgg(column='location_type', aggfunc='last')
    ).reset_index()
    
    # Merge aggregated data back
    icu_df = pd.merge(
        icu_block[["encounter_block", "icu_group", "icu_rank"]],
        icu_block2,
        on=["encounter_block", 'icu_group'],
        how="left"
    )
    
    # Step 6: Update ICU rank by ICU group
    icu_adt_final = icu_df.sort_values(by=['encounter_block', 'icu_rank', 'icu_group'])
    icu_adt_final['icu_rank'] = icu_adt_final.groupby(['encounter_block', 'icu_group']).ngroup() + 1
    icu_adt_final['icu_rank'] = (
        icu_adt_final.groupby('encounter_block')['icu_rank']
        .rank(method='dense')
        .astype(int)
    )
    
    return icu_adt_final