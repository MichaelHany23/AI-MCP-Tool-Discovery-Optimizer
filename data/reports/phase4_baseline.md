# Phase 4 offline baseline

This is a deterministic control run, not an LLM result. It intentionally
selects a confusable tool for one out of every four eligible tasks so the
scoring and confusion-matrix pipeline can be checked end to end.

| Split | Selection | Arguments | Order | Task success |
|---|---:|---:|---:|---:|
| train | 73.3% | 100.0% | 73.3% | 73.3% |
| dev | 75.0% | 100.0% | 75.0% | 75.0% |
| test | 77.8% | 100.0% | 77.8% | 77.8% |

## Top confusions

### train
- Expected `find_contact`, selected `search_accounts`: 8 task(s)
- Expected `query_sales`, selected `sum_revenue`: 8 task(s)
- Expected `search_events`, selected `list_events`: 8 task(s)
- Expected `search_files`, selected `read_file`: 8 task(s)
- Expected `search_issues`, selected `find_issues`: 8 task(s)
### dev
- Expected `find_contact`, selected `search_accounts`: 3 task(s)
- Expected `query_sales`, selected `sum_revenue`: 3 task(s)
- Expected `search_events`, selected `list_events`: 3 task(s)
- Expected `search_files`, selected `read_file`: 3 task(s)
- Expected `search_issues`, selected `find_issues`: 3 task(s)
### test
- Expected `find_contact`, selected `search_accounts`: 4 task(s)
- Expected `query_sales`, selected `sum_revenue`: 4 task(s)
- Expected `search_events`, selected `list_events`: 4 task(s)
- Expected `search_files`, selected `read_file`: 4 task(s)
- Expected `search_issues`, selected `find_issues`: 4 task(s)
