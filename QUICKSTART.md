# Project Aegis - Quick Start Guide

Get up and running with the Clinical Control Tower demo in minutes.

**Prerequisites:** [Snowflake CLI](https://docs.snowflake.com/en/developer-guide/snowflake-cli/installation/installation) installed (`pip install snowflake-cli-labs`) and configured with your Snowflake connection.

## 🚀 Fast Setup (5 Minutes)

### 1. Run Snowflake Setup

Connect to your Snowflake account and execute these scripts in order:

```sql
-- In Snowflake Worksheet or Snowflake CLI:

-- Step 1: Set demo date (5 seconds)
@sql/01_set_demo_date.sql

-- Step 2: Create database, schemas, and tables (30 seconds)
@sql/02_create_raw_schema.sql

-- Step 3: Generate base data (60 seconds)
@sql/03_generate_base_data.sql

-- Step 4: Generate subjects (30 seconds)
@sql/04_generate_enrollment.sql

-- Step 5: Add screen failures (15 seconds)
@sql/05_add_screen_failures.sql

-- Step 6: Create analytical views (30 seconds)
@sql/06_create_views.sql

-- Step 7: Create forecast tool (10 seconds)
@sql/07_create_forecast_tool.sql

-- Step 8: Load SOPs (optional, 10 seconds)
@sql/08_load_playbook.sql
```

**Using Snowflake CLI:**
```bash
cd sql
for script in 01_set_demo_date.sql 02_create_raw_schema.sql \
              03_generate_base_data.sql 04_generate_enrollment.sql \
              05_add_screen_failures.sql 06_create_views.sql \
              07_create_forecast_tool.sql 08_load_playbook.sql; do
  snow sql -f $script
done
```

### 2. Install Python Dependencies

```bash
# Navigate to project directory
cd demo_aegis_cct

# Option A: Using Conda (recommended)
conda env create -f environment.yml
conda activate aegis_cct

# Option B: Using pip
pip install -r requirements.txt
```

### 3. Configure Snowflake Connection

```bash
# Copy template
cp app/.streamlit/secrets.toml.template app/.streamlit/secrets.toml

# Edit with your credentials (use your favorite editor)
nano app/.streamlit/secrets.toml
```

Required values:
```toml
[snowflake]
account = "orgname-accountname"        # e.g., "myorg-myaccount"
user = "your_username"
password = "your_password"
role = "ACCOUNTADMIN"                  # or your role
warehouse = "COMPUTE_WH"               # or your warehouse
database = "AEGIS_CCT"
schema = "COMBINED"
```

### 4. Launch the Dashboard

```bash
cd app
streamlit run Home.py
```

The dashboard will open automatically at `http://localhost:8501`

## 📊 Demo Walkthrough

### The Story
Your portfolio has 15 clinical trials. One trial (VT-501) is significantly behind schedule, projecting a 3-month delay. Your job: find out why.

### Follow This Path

1. **Start at Portfolio View**
   - Notice: 15 trials, 200 sites, 25 countries
   - See: 1 trial is marked "Off Track" (in red)
   - That's VT-501: "COPD Exacerbation Prevention Study"

2. **Click on VT-501 to drill down**
   - Select VT-501 from the trial dataframe
   - See: Only ~78% enrollment complete vs plan
   - See: 5 sites are marked "Off Track" (laggard sites)
   - Those are SITE-100, SITE-102, SITE-104, SITE-106, SITE-108

3. **Click on SITE-100 to investigate**
   - Select SITE-100 from the dataframe
   - **Smoking Gun #1**: CRA Notes say "PI was not available for visit. Staff seems disengaged."
   - **Smoking Gun #2**: Multiple overdue tasks
   - **Root Cause Identified**: Site management and PI engagement problem

4. **Check other laggard sites** (same pattern)
   - SITE-102, 104, 106, 108 show similar issues
   - All achieve only 0-10% of planned enrollment
   - Confirms this is a systematic problem at these five sites

### Key Insights to Highlight

✓ Real-time visibility across entire portfolio  
✓ Drill-down capability from portfolio → trial → site  
✓ Clear identification of problem areas (visual color coding)  
✓ Root cause analysis through integrated operational data  
✓ Actionable insights (need to replace or intervene at these sites)

## 🎯 Key Features to Demonstrate

| Feature | Where to Show | What to Say |
|---------|---------------|-------------|
| **Portfolio KPIs** | Page 1 | "One dashboard for all trials, sites, and countries" |
| **Trend Analysis** | Page 1 chart | "We can see enrollment falling behind plan over time" |
| **Trial Status** | Page 1 table | "Color coding makes problem trials immediately visible" |
| **Drill-Down** | Navigation | "Click through from portfolio to trial to specific site" |
| **Root Cause** | Page 3 notes | "CRA notes reveal the actual problem: PI engagement" |
| **Operational Data** | Page 3 tasks | "Overdue tasks confirm the site isn't functioning properly" |

## 🐛 Troubleshooting

### "Cannot connect to Snowflake"
- Check `app/.streamlit/secrets.toml` exists (not `.template`)
- Verify credentials are correct
- Test connection: `snow connection test`
- Ensure warehouse is running

### "No data showing in dashboard"
- Verify all three SQL scripts completed successfully
- Check data: `SELECT COUNT(*) FROM AEGIS_CCT.RAW.CTMS.study__v;` (should return 15)
- Confirm database/schema names in secrets.toml match

### "Module not found" errors
- Activate conda environment: `conda activate aegis_cct`
- Or reinstall: `pip install -r requirements.txt`

### "Page is blank"
- Check browser console for errors
- Try: `streamlit cache clear`
- Restart the app

## 📞 Quick Commands

```bash
# Restart the app
# Press Ctrl+C in terminal, then:
streamlit run app/Home.py

# Clear cache
streamlit cache clear

# Check if data loaded
snow sql -q "SELECT COUNT(*) FROM AEGIS_CCT.RAW.CTMS.study__v;"

# View Streamlit logs
# They appear in the terminal where you ran streamlit
```

## ✅ Verification Checklist

Before presenting:
- [ ] All SQL scripts ran without errors
- [ ] Dashboard connects to Snowflake (checkmark in sidebar)
- [ ] Portfolio view shows 15 trials, 200 sites
- [ ] VT-501 is marked "Off Track" with projected delay
- [ ] Can drill down from VT-501 by selecting row
- [ ] Time series chart shows actual vs planned enrollment
- [ ] SITE-100 shows "PI was not available" in CRA notes (via AI Assistant)
- [ ] Laggard sites (100, 102, 104, 106, 108) show low enrollment
- [ ] Multi-page navigation works (Enrollment, AI Assistant, SOPs)

## 🎤 Presentation Tips

**Opening**: "Let me show you how Snowflake unifies clinical trial data to provide real-time operational intelligence."

**During Demo**: 
- Click confidently through the drill-down
- Point out the visual indicators (red = problem)
- Highlight how quickly you identified the root cause
- Emphasize "all from one unified data platform"

**Closing**: "In minutes, we identified the problem, found the root cause, and can now take action. This is the power of unified data analytics."

---

Need help? Check the full [README.md](README.md) for detailed documentation.

