/* ========================================================================
   EARLY WARNING MODEL - STANDALONE CODE
   
   Join 2019 Skills with 2023 Churn Rate
======================================================================== */

/* Step 1: Set file paths */
%let data_path = /export/viya/homes/spendyala1@hawk.illinoistech.edu;

/* Step 2: Import 2019 Training Data (contains 2019 skills) */
proc import datafile="&data_path/train_2019.csv"
    out=work.data_2019
    dbms=csv
    replace;
    getnames=yes;
run;

/* Step 3: Import 2023 Validation Data (contains 2023 churn) */
proc import datafile="&data_path/validate_2023.csv"
    out=work.data_2023
    dbms=csv
    replace;
    getnames=yes;
run;

/* Step 4: Preview both datasets */
proc print data=work.data_2019(obs=5);
    title "2019 Data - First 5 Rows";
run;

proc print data=work.data_2023(obs=5);
    title "2023 Data - First 5 Rows";
run;

proc contents data=work.data_2019;
    title "2019 Data Structure";
run;

proc contents data=work.data_2023;
    title "2023 Data Structure";
run;

/* Step 5: Extract ONLY Skills from 2019 (Features = X) */
data work.skills_2019;
    set work.data_2019;
    /* Keep only region and skill/context features */
    /* Drop 2019 churn - we don't need it */
    drop target_churn;
run;

proc print data=work.skills_2019(obs=5);
    var region CX_ConsequenceofError CX_ContactWithOthers SK_ActiveLearning SK_ActiveListening;
    title "2019 Skills (Features Only) - Sample";
run;


/* Step 6: Extract ONLY Region and Churn from 2023 (Target = Y) */
data work.churn_2023;
    set work.data_2023;
    /* Keep only region and target churn from 2023 */
    keep region target_churn;
    /* Rename to clarify this is 2023 churn */
    rename target_churn = target_churn_2023;
run;

proc print data=work.churn_2023(obs=10);
    title "2023 Churn Rates by Region";
run;

/* Step 7: JOIN 2019 Skills with 2023 Churn by Region */
proc sql;
    create table work.early_warning_table as
    select 
        a.region,
        a.*,                      /* All 2019 skill columns (CX_*, SK_*) */
        b.target_churn_2023      /* 2023 churn as target variable */
    from work.skills_2019 as a
    inner join work.churn_2023 as b
    on a.region = b.region
    order by a.region;
quit;

/* Step 8: Verify the join worked correctly */
proc print data=work.early_warning_table(obs=10);
    title "===== EARLY WARNING TABLE: 2019 Skills → 2023 Churn =====";
run;

/* Step 9: Check data quality */
proc sql;
    select 
        'Data Summary' as Info,
        count(*) as Total_Regions,
        count(distinct region) as Unique_Regions,
        sum(case when target_churn_2023 is null then 1 else 0 end) as Missing_Churn_2023,
        sum(case when target_churn_2023 is not null then 1 else 0 end) as Valid_Records
    from work.early_warning_table;
quit;

/* Step 10: Statistics on 2023 Churn */
proc means data=work.early_warning_table n nmiss mean std min max;
    var target_churn_2023;
    title "2023 Churn Rate Statistics";
run;


/* Load to CAS, Truncate Names to 32 bytes, and Promote */
proc casutil;
   load data=work.early_warning_table 
        casout="TRAIN DATA 2019 & 2023" 
        outcaslib="public" 
        promote;
run;
