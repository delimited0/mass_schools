library(data.table)
library(ggplot2)

# SAT over time ----

dt = fread("SAT_Performance_20260605.csv")

dt[
  ORG_NAME == "Watertown High" & STU_GRP == "English Learners",
]

dt[
  ORG_NAME == "Arlington High" & STU_GRP == "English Learners",
]

dt[
  ORG_NAME == "Arlington High" & STU_GRP == "Low Income",
]

dt[
  ORG_NAME == "Watertown High" & SY == 2025,
]

dt[
  ORG_NAME == "Lexington High" & SY == 2025,
]

dt[
  ORG_NAME == "Lexington High",
STU_GRP] |> unique()

dt[, ORG_TYPE] |> unique()

annual_org_scores = dt[
  STU_GRP == "All Students", 
  .(SY, ORG_NAME, READ_SCORE, WRITE_SCORE, MATH_SCORE)
][
  ORG_NAME != "State"
]

ggplot(annual_org_scores, aes(x = SY, y = MATH_SCORE, group = ORG_NAME)) +
  geom_line() +
  labs(title = "SAT Math Scores Over Time by Organization",
       x = "School Year",
       y = "Average Math Score") +
  theme_minimal() +
  theme(legend.position = "none")


dt[!is.na(READ_SCORE), summary(SY)]
dt[!is.na(READ_WRITE_SCORE), summary(SY)]



# discipline data ----
discipline_df = fread("Student_Discipline_20260616.csv")

discipline_df[, SY] |> min()

discipline_df[, OFFENSE] |> unique()

discipline_df[, STU_GRP] |> unique()


# mcas data ----
mcas_df = fread("MCAS_Performance_20260616.csv")