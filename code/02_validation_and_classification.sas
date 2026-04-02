/* ========================================================================
   CALCULATE TOTAL EMPLOYMENT BY REGION - 2019 vs 2023
   
   Sums TOT_EMP across all detailed occupations for each region
   ======================================================================== */

%let data_path = /export/viya/homes/spendyala1@hawk.illinoistech.edu;

/* ========================================================================
   STEP 1: IMPORT 2019 OEWS DATA
   ======================================================================== */

proc import datafile="&data_path/BLS_OEWS_MSA_2019.xlsx"
    out=work.oews_2019_raw
    dbms=xlsx
    replace;
run;

/* Preview the data */
proc print data=work.oews_2019_raw(obs=5);
    title "2019 OEWS Data - First 5 Rows";
run;

proc contents data=work.oews_2019_raw;
    title "2019 OEWS Data Structure";
run;

/* ========================================================================
   STEP 2: CALCULATE 2019 EMPLOYMENT BY REGION
   ======================================================================== */

/* Clean and convert tot_emp to numeric */
data work.oews_2019_clean;
    set work.oews_2019_raw;
    
    /* Convert tot_emp from text to numeric (remove commas) */
    tot_emp_num = input(compress(tot_emp, ','), best.);
    
    /* Keep only detailed occupations */
    where upcase(o_group) = 'DETAILED';
run;

/* Sum employment by region */
proc sql;
    create table work.employment_2019 as
    select 
        area_title as region,
        sum(tot_emp_num) as total_employment_2019,
        count(distinct occ_code) as n_occupations_2019
    from work.oews_2019_clean
    where tot_emp_num > 0
      and area_title is not missing
    group by area_title;
quit;

/* Display 2019 results */
proc print data=work.employment_2019;
    title "2019 Total Employment by Region";
run;

/* ========================================================================
   STEP 3: IMPORT 2023 OEWS DATA
   ======================================================================== */

proc import datafile="&data_path/BLS_OEWS_MSA_2023.xlsx"
    out=work.oews_2023_raw
    dbms=xlsx
    replace;
run;

/* Preview the data */
proc print data=work.oews_2023_raw(obs=5);
    title "2023 OEWS Data - First 5 Rows";
run;

/* ========================================================================
   STEP 4: CALCULATE 2023 EMPLOYMENT BY REGION
   ======================================================================== */

/* Clean and convert TOT_EMP to numeric */
data work.oews_2023_clean;
    set work.oews_2023_raw;
    
    /* Convert TOT_EMP from text to numeric (remove commas) */
    tot_emp_num = input(compress(TOT_EMP, ','), best.);
    
    /* Keep only detailed occupations */
    where upcase(O_GROUP) = 'DETAILED';
run;

/* Sum employment by region */
proc sql;
    create table work.employment_2023 as
    select 
        AREA_TITLE as region,
        sum(tot_emp_num) as total_employment_2023,
        count(distinct OCC_CODE) as n_occupations_2023
    from work.oews_2023_clean
    where tot_emp_num > 0
      and AREA_TITLE is not missing
    group by AREA_TITLE;
quit;

/* Display 2023 results */
proc print data=work.employment_2023(obs=20);
    title "2023 Total Employment by Region";
run;

/* ========================================================================
   STEP 5: COMPARE 2019 vs 2023 EMPLOYMENT
   ======================================================================== */

proc sql;
    create table work.employment_comparison as
    select 
        coalesce(a.region, b.region) as region,
        a.total_employment_2019,
        a.n_occupations_2019,
        b.total_employment_2023,
        b.n_occupations_2023,
        b.total_employment_2023 - a.total_employment_2019 as employment_change,
        case 
            when a.total_employment_2019 > 0 then
                ((b.total_employment_2023 - a.total_employment_2019) / a.total_employment_2019) * 100
            else .
        end as pct_change
    from work.employment_2019 a
    full join work.employment_2023 b
    on a.region = b.region
    order by total_employment_2019 descending;
quit;

/* ========================================================================
   STEP 6: DISPLAY COMPARISON RESULTS
   ======================================================================== */

/* Overall summary */
proc means data=work.employment_comparison n sum mean std min max;
    var total_employment_2019 total_employment_2023 employment_change pct_change;
    title "Employment Statistics Summary Across All Regions";
run;

/* Top 20 regions by 2019 employment */
proc print data=work.employment_comparison(obs=20);
    title "Top 20 Regions by Total Employment (2019)";
    title2 "With 2023 Comparison";
run;

/* Regions with largest absolute growth */
proc sort data=work.employment_comparison;
    by descending employment_change;
run;

proc print data=work.employment_comparison(obs=15);
    title "Top 15 Regions by Employment Growth (2019-2023)";
    title2 "Absolute Change";
    var region total_employment_2019 total_employment_2023 
        employment_change pct_change;
    format total_employment_2019 total_employment_2023 employment_change comma12.;
    format pct_change 8.2;
run;

/* Regions with largest percentage growth */
proc sort data=work.employment_comparison;
    by descending pct_change;
run;

proc print data=work.employment_comparison(obs=15);
    title "Top 15 Regions by Employment Growth (2019-2023)";
    title2 "Percentage Change";
    var region total_employment_2019 total_employment_2023 
        employment_change pct_change;
    format total_employment_2019 total_employment_2023 employment_change comma12.;
    format pct_change 8.2;
run;

/* Regions with largest decline */
proc sort data=work.employment_comparison;
    by employment_change;
run;

proc print data=work.employment_comparison(obs=15);
    title "Top 15 Regions by Employment Decline (2019-2023)";
    var region total_employment_2019 total_employment_2023 
        employment_change pct_change;
    format total_employment_2019 total_employment_2023 employment_change comma12.;
    format pct_change 8.2;
run;

/* ========================================================================
   STEP 7: VISUALIZATIONS
   ======================================================================== */

/* Top 15 regions by 2019 employment - comparison bar chart */
proc sort data=work.employment_comparison;
    by descending total_employment_2019;
run;

data work.top15_regions;
    set work.employment_comparison(obs=15);
run;

proc sgplot data=work.top15_regions;
    vbar region / response=total_employment_2019 name='2019' 
                  fillattrs=(color=blue) transparency=0.3;
    vbar region / response=total_employment_2023 name='2023' 
                  fillattrs=(color=red) transparency=0.3 barwidth=0.6;
    xaxis display=(nolabel) discreteorder=data fitpolicy=rotate;
    yaxis label="Total Employment" grid;
    keylegend '2019' '2023' / title="Year";
    title "Top 15 Regions: Employment Comparison (2019 vs 2023)";
    format total_employment_2019 total_employment_2023 comma10.;
run;

/* Scatter plot: Absolute change vs Percentage change */
proc sgplot data=work.employment_comparison;
    scatter x=employment_change y=pct_change / markerattrs=(size=8);
    refline 0 / axis=x lineattrs=(color=red pattern=dash);
    refline 0 / axis=y lineattrs=(color=red pattern=dash);
    xaxis label="Absolute Employment Change" grid;
    yaxis label="Percentage Change (%)" grid;
    title "Employment Growth: Absolute vs Percentage Change";
run;

/* Distribution of percentage changes */
proc sgplot data=work.employment_comparison;
    histogram pct_change / nbins=30;
    density pct_change / type=kernel;
    xaxis label="Percentage Change in Employment (%)";
    yaxis label="Frequency";
    title "Distribution of Employment Percentage Changes (2019-2023)";
run;

/* ========================================================================
   STEP 8: EXPORT RESULTS
   ======================================================================== */
cas mySession sessopts=(caslib=casuser timeout=1800 locale="en_US");
caslib _all_ assign;

   proc casutil;
   load data=work.employment_comparison 
        casout="EMPLOYMENT COMAPARISON 2019 & 2023" 
        outcaslib="public" 
        promote;
    run;


/* ========================================================================
   CREATE FALSE GROWTH TABLE
   ======================================================================== */

libname casuser cas caslib="casuser";

proc sql;
    create table work.false_growth_table as
    select 
        a.region,
        a.P_target_churn_2023 as Predicted_Churn_2023,
        b.pct_change as Employment_Growth_Pct
    from casuser.PREDICTED_CHURN_2023_FROM_2019_S as a
    left join work.employment_comparison as b
    on a.region = b.region
    order by a.region;
quit;

proc print data=work.false_growth_table;
    title "False Growth Table";
run;

proc casutil;
   load data=work.false_growth_table 
        casout="false_growth_rate" 
        outcaslib="public" 
        promote;
    run;


/* ========================================================================
   DEFINE HIGH VS LOW - FALSE GROWTH QUADRANTS
   ======================================================================== */

proc means data=work.false_growth_table noprint;
    var Predicted_Churn_2023 Employment_Growth_Pct;
    output out=casuser.medians
        median(Predicted_Churn_2023)=median_churn
        median(Employment_Growth_Pct)=median_growth;
run;

proc sql;
    create table work.false_growth_labeled as
    select
        a.region,
        a.Predicted_Churn_2023,
        a.Employment_Growth_Pct,
        b.median_churn,
        b.median_growth,

        /* High / Low flags */
        case 
            when a.Predicted_Churn_2023 > b.median_churn 
            then 1 else 0 
        end as High_Churn_Risk,

        case 
            when a.Employment_Growth_Pct > b.median_growth 
            then 1 else 0 
        end as High_Growth

    from work.false_growth_table a
    cross join casuser.medians b;
quit;

proc sql;
    create table work.false_growth_quadrants as
    select
        *,
        case
            when High_Growth = 1 and High_Churn_Risk = 1 then 'False Growth'
            when High_Growth = 1 and High_Churn_Risk = 0 then 'True Growth'
            when High_Growth = 0 and High_Churn_Risk = 1 then 'Fragile / Decline'
            else 'Stable'
        end as Growth_Type
    from work.false_growth_labeled;
quit;


proc freq data=work.false_growth_quadrants;
    tables Growth_Type;
run;

proc print data=work.false_growth_quadrants;
run;

/* loadind to casuser */
proc casutil;
    load data=work.false_growth_quadrants
    outcaslib="casuser" 
    casout="False_Growth_Quadrants" 
    promote;
quit;



/*-----------------------------------------------------------
  FALSE GROWTH QUADRANT PLOT (Code-only, judge-friendly)
  X: Employment Growth %
  Y: Predicted 2023 Churn (from 2019 skills)
  Reference lines: medians
-----------------------------------------------------------*/

ods graphics / reset width=1100px height=650px imagename="false_growth_quadrant";

/* 1) Compute medians and store them in macro variables */
proc sql noprint;
  select median(Employment_Growth_Pct),
         median(Predicted_Churn_2023)
    into :med_growth, :med_churn
  from work.false_growth_quadrants;
quit;

%put &=med_growth &=med_churn;

/* 2) Build the scatter plot with median reference lines */
title "False Growth Quadrant: Growth vs Predicted Churn Risk (2019 - 2023)";
title2 "Vertical line = Median Employment Growth | Horizontal line = Median Predicted Churn";

proc sgplot data=work.false_growth_quadrants;
  scatter x=Employment_Growth_Pct y=Predicted_Churn_2023 /
          group=Growth_Type
          transparency=0.15
          markerattrs=(symbol=circlefilled size=7);

  /* Median reference lines */
  refline &med_growth / axis=x lineattrs=(pattern=shortdash thickness=2) label="Median growth";
  refline &med_churn  / axis=y lineattrs=(pattern=shortdash thickness=2) label="Median predicted churn";

  /* Label the top-right quadrant (False Growth zone) */
  inset "False Growth:" "Expansion masking instability"
        / position=topright border;

  xaxis label="Employment Growth (%) (2019 - 2023)";
  yaxis label="Predicted 2023 Churn (%) (from 2019 skills)";
  keylegend / title="Quadrant Label";
run;

title;



/* ========================================================================
   VALIDATION 1 - THAT FALSE GROWTH IS REAL 
   ======================================================================== */

libname casuser cas caslib = "casuser";

proc sql;
    create table work.False_Growth_Quadrants_v1 as
    select
        a.*,
        b.target_churn_2023 as Actual_Churn_2023
    from casuser.False_Growth_Quadrants a
    left join casuser.PREDICTED_CHURN_2023_FROM_2019_S b
        on a.region = b.region;
quit;

proc print data = work.False_Growth_Quadrants_v1; run; 

proc means data=work.False_Growth_Quadrants_v1 mean std n;
    class Growth_Type;
    var Actual_Churn_2023;
    where Growth_Type in ("False Growth", "True Growth");
run;


proc ttest data=work.False_Growth_Quadrants_v1;
    class Growth_Type;
    var Actual_Churn_2023;
    where Growth_Type in ("False Growth", "True Growth");
run;


/* =========================================================
   VALIDATION 2 — Employment illusion check
   Compare employment growth across Growth Types
   ========================================================= */

proc means data=work.False_Growth_Quadrants_v1 mean std n;
    class Growth_Type;
    var Employment_Growth_Pct;
    where Growth_Type in ("False Growth", "True Growth");
run;

proc ttest data=work.False_Growth_Quadrants_v1;
    class Growth_Type;
    var Employment_Growth_Pct;
    where Growth_Type in ("False Growth", "True Growth");
run;


/* =========================================================
   VALIDATION 3 — Concentration of False Growth
   ========================================================= */

proc sql;
    select
        count(*) as High_Growth_Regions,
        sum(case when Growth_Type = "False Growth" then 1 else 0 end)
            as False_Growth_Regions,
        calculated False_Growth_Regions / calculated High_Growth_Regions * 100
            as False_Growth_Share format=6.2
    from work.False_Growth_Quadrants_v1
    where High_Growth = 1;
quit;

proc freq data=work.False_Growth_Quadrants_v1;
    tables Growth_Type;
    where High_Growth = 1;
run;
