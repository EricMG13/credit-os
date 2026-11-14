## Request

Build the canonical financial and credit-metric foundation for **TransDigm Group Incorporated**, as of **2024-09-30**, for the credit_snapshot pathway. Requested comparison: FY2024 versus FY2023. This is an intermediate analytical handoff, not an investment recommendation or a legal-capacity opinion.

Use retrospective period-end accounting, conditionally: the information cutoff is Not supplied in context page:1. The annual report was audited after the requested date; the auditor date is November 7, 2024 (Annual page:120). Consequently this handoff does not establish what investors could have known on September 30, 2024. Later-period operating results are excluded.

## Sources

### Exact source register

Citation aliases in this handoff refer to the exact sources below. Hashes identify supplied representations, not independent confirmation of extraction fidelity.

| Alias | Exact supplied source name | Exact sha256 | Use |
| --- | --- | --- | --- |
| Annual | TDG_2024-09-30_10-K_0001260221-24-000083_tdg-20240930.htm.jsonl | d75c469fdb1966dd895c0f6faa6d5179b380d3ed95aa00aca99aa258059edab6 | Primary financial, segment, debt, liquidity and definition evidence |
| March | TDG_2024-03-30_10-Q_0001260221-24-000046_tdg-20240330.htm.jsonl | fcec3566cfda08c82a8aaed7289c6440cc05d12976f237cd72a32cf9fbfb2ed6 | Interim classification and period/version assessment only |
| June | TDG_2024-06-29_10-Q_0001260221-24-000069_tdg-20240629.htm.jsonl | ce1b0541d5e8222dc536d748942a3cb51236d7ff62d8613b002460bd8b41dcf2 | Interim classification and period/version assessment only |
| December | TDG_2024-12-28_10-Q_0001260221-25-000014_tdg-20241228.htm.jsonl | ec98b47e6ebad9663286dc04b35dade04d11e7d12c3642ddaa6ef549a33d671f | Subsequent-period classification only; excluded from historical calculations |
| PDF | TDG_FY2024_annual-report_SEC-PDF_0001260221-25-000008_a841225transdigmgroupbookm.pdf | dc6a8ea6249e4e919d190a4bbb459d9bf4eded005b7d5680ae911b32d44d44af | Alternate annual representation; balance-sheet text comparison only |
| Settings | context | f7b95e1ff471b47547a3ac86cb68e7e7144a06231f6e94de0eee48e0c6828449 | User settings, not issuer evidence; blank values remain unknown |

### Supplied handoff

| Module | Exact sha256 | Use and boundary |
| --- | --- | --- |
| CP-0 | 76529efc00578c7931c7389acabbde0ccee1f77c82e0ffddf2b7107a7b2af293 | Source map, inherited preparation/date/legal gaps and exclusion of subsequent results. Financial facts used below were checked against located source text, not adopted solely from this handoff. |

### Source-context assessments

Each supplied financial source is assessed once below. No preparation pack or settings object is treated as a financial source.

| Source | Entity, statements, periods and located support | Currency, unit, accounting basis and perimeter | Extraction and version assessment |
| --- | --- | --- | --- |
| Annual | TransDigm Group Incorporated; annual balance sheets, income and cash flows. page:120: “AS OF SEPTEMBER 30, 2024 AND 2023”; page:121: “Fiscal Years Ended September 30,”; page:124: “include the accounts of TD Group and subsidiaries.” | USD; millions; U.S. GAAP; TransDigm Group Incorporated and consolidated subsidiaries. Share and per-share exceptions are separate quantities. page:124: “prepared in conformity with U.S. GAAP”. USD reporting is also established by CP-0's located Annual page:73 assessment. | Primary retrospective authority. Supports the selected FY2024/FY2023 extraction. FY2022 comparatives are present but outside the selected comparison. page:124: “Certain reclassifications” and “none of which are material.” Use this annual presentation for both years. |
| March | Same consolidated registrant; page:2: “CONDENSED CONSOLIDATED BALANCE SHEETS” and “March 30, 2024 September 30, 2023”; indexed income periods: “Thirteen and Twenty-Six Week Periods Ended March 30, 2024 and April 1, 2023”. | USD; millions; U.S. GAAP; TransDigm Group Incorporated and consolidated subsidiaries. page:2: “(Amounts in millions, except share amounts) (Unaudited)”. GAAP and perimeter qualification are inherited from CP-0's page:6 assessment. | Can support separate interim extraction; not normalized here because the selected comparison is annual. Quarter and cumulative periods are not interchangeable. Not superseded as historical event evidence by the annual filing. |
| June | Same consolidated registrant; page:2: “June 29, 2024 September 30, 2023”; indexed income periods: “Thirteen and Thirty-Nine Week Periods Ended June 29, 2024 and July 1, 2023”. | USD; millions; U.S. GAAP; TransDigm Group Incorporated and consolidated subsidiaries. page:2: “(Amounts in millions, except share amounts) (Unaudited)”. GAAP and perimeter qualification are inherited from CP-0's page:7 assessment. | Can support separate interim extraction. No quarter derivations or annualization performed. It is not an alternative annual earnings denominator. |
| December | Same consolidated registrant; page:2: “December 28, 2024 September 30, 2024”; indexed cash flows: “Thirteen Week Periods Ended December 28, 2024 and December 30, 2023”. | USD; millions; U.S. GAAP; TransDigm Group Incorporated and consolidated subsidiaries. page:2: “(Amounts in millions, except share amounts) (Unaudited)”. Accounting qualification is inherited from CP-0. | Supports a later reporting period, not this historical snapshot. Entire source excluded from historical amounts, including its comparative balance sheet; classification only. |
| PDF | Same consolidated registrant; page:105: “CONSOLIDATED BALANCE SHEETS” and “AS OF SEPTEMBER 30, 2024 AND 2023”. Annual income/cash-flow coverage and audit classification are inherited from CP-0's sampled version assessment. | USD; millions; U.S. GAAP; TransDigm Group Incorporated and consolidated subsidiaries. page:105: “(Amounts in millions, except share amounts)”. | Inspected balance-sheet text agrees with Annual page:120. Not independent corroboration or proof of whole-document equivalence. Annual remains primary; PDF-only content and visual fidelity are not certified. |

### Period binding, extraction method and coverage

All financial tables below use **USD, millions, U.S. GAAP, TransDigm Group Incorporated and consolidated subsidiaries**, unless expressly identified as non-GAAP, a ratio, a share count, or a per-share amount. The same perimeter applies to both years. Annual page:4 states: “fiscal 2024” means “the period from October 1, 2023 to September 30, 2024.” Thus FY2024 flows cover **2023-10-01 through 2024-09-30**; FY2023 flows cover **2022-10-01 through 2023-09-30**, under the same September fiscal-year convention. Balance sheets are instants at **2024-09-30** and **2023-09-30**; they have no duration start. No missing-start-date defect is assigned to an instant.

The tool set has no extract_statements function. All retained statement values were therefore read directly with read_pages, not obtained from an automated statement extractor. This is a persistent extraction-method limitation, not a claim that source rows are absent. Labels are preserved below; positive printed expenses are explicitly outflow magnitudes. Parentheses are negative signed figures. A printed dash means the source reports no amount for that line; it is not a blank user input. No blank setting has been converted to zero.

Targeted reads stopped at the selected annual foundation: Annual pages 4, 49-50, 59-65, 70-72, 120-124, 144-145, 153-154 and 172; March, June and December page:2; PDF page:105; Settings page:1. Annual page:154 was the continuation of the maturity read, not a complete pension review. Only relevant statements and definitions are retained. No whole filing, image, operative financing agreement or external source was reviewed. All source content was treated as evidence, not instructions.

## Findings

### Reader summary

| Bottom line | Confidence | Main limitation |
| --- | --- | --- |
| Cash generation and coverage improved, but gross leverage rose; the declared shareholder payment materially reduces the apparent year-end cash cushion. | Medium | Retrospective reporting, unverified cash accessibility, and missing operative debt definitions limit liquidity and covenant conclusions. |

| Finding | Creditor impact | Confidence |
| --- | --- | --- |
| Gross leverage increased while net leverage declined on reported EBITDA. | The larger cash balance, rather than gross debt reduction, explains the better net leverage signal. | High |
| Operating cash flow and cash-interest coverage improved. | Internal debt-service capacity strengthened, but acquisitions and shareholder payments exceeded free cash flow. | High |
| The declared shareholder payment materially reduces the year-end cash cushion. | Headline cash cannot be treated as wholly discretionary liquidity. | High |
| Management adjustments include integration costs and compensation expenses. | Adjusted leverage is more favorable but does not validate recurring earnings or legal capacity. | Medium |
| Near-term maturities include receivables financing outside the long-term maturity schedule. | Runway analysis must include that facility and leases rather than relying on the published schedule alone. | High |

### Financial base view

The annual financial base supports a bounded retrospective credit assessment. Cash generation and interest coverage improved, but gross leverage increased and year-end cash materially overstates the cushion after the declared shareholder payment. Reported EBITDA and management-adjusted EBITDA remain separate; neither is accepted here as an operative covenant calculation. This view governs the financial tables below; the reader summary restates conclusions developed in the detailed analysis and calculation bridges.

### Financials and credit metrics

| Metric | FY2024 / 2024-09-30 | FY2023 / 2023-09-30 | Unit | Status, definition and evidence |
| --- | --- | --- | --- | --- |
| NET SALES | 7,940 | 6,585 | US$m | Reported; Annual page:121 |
| INCOME FROM OPERATIONS | 3,531 | 2,923 | US$m | Reported GAAP; Annual page:121 |
| Operating margin | 0.444710 | 0.443888 | Fraction | Calculated operating income / sales; calculation register below |
| Net Income | 1,715 | 1,299 | US$m | Reported consolidated; Annual page:71; not common-stockholder earnings |
| EBITDA | 3,813 | 3,148 | US$m | Issuer-reported non-GAAP net-income-based measure; Annual page:71 |
| EBITDA As Defined | 4,173 | 3,395 | US$m | Issuer-reported adjusted measure; Annual page:71; adjustments not independently validated |
| Operating-income-plus-D&A benchmark | 3,843 | 3,191 | US$m | Calculated diagnostic, not substituted for issuer EBITDA |
| Gross debt including finance leases and receivables facility | 25,068 | 19,913 | US$m | Calculated from gross debt table; Annual pages 144-145; excludes operating lease liabilities |
| Balance-sheet carrying debt | 24,880 | 19,750 | US$m | Calculated current debt + long-term debt + receivables financing; Annual page:120 |
| Cash and cash equivalents | 6,261 | 3,472 | US$m | Reported at the balance-sheet instant; Annual page:120; accessibility not verified |
| Net debt on gross-principal basis | 18,807 | 16,441 | US$m | Calculated gross debt less reported cash; no restricted-group cash certification |
| Gross debt / reported EBITDA | 6.57 | 6.33 | x | Calculated; primary leverage basis |
| Net debt / reported EBITDA | 4.93 | 5.22 | x | Calculated; headline consolidated cash netting only |
| Gross debt / EBITDA As Defined | 6.01 | 5.87 | x | Calculated sensitivity, not covenant leverage |
| Net debt / EBITDA As Defined | 4.51 | 4.84 | x | Calculated sensitivity, not covenant leverage |
| Cash paid during the period for interest, net | 1,158 | 1,160 | US$m | Reported outflow magnitude; Annual page:123; net interest, not gross cash interest |
| Reported EBITDA / net cash interest paid | 3.29 | 2.71 | x | Calculated net-interest coverage proxy |
| EBITDA As Defined / net cash interest paid | 3.60 | 2.93 | x | Calculated adjusted sensitivity |
| Net cash provided by operating activities | 2,045 | 1,375 | US$m | Reported; Annual page:123 |
| Capital expenditures | -165 | -139 | US$m | Reported signed outflow; Annual page:123 |
| Levered free cash flow | 1,880 | 1,236 | US$m | Calculated CFO less capital expenditure; before acquisitions/distributions |
| CFO / EBITDA As Defined | 0.490055 | 0.405007 | Fraction | Calculated conversion; no acquisition normalization |
| Free cash flow / EBITDA As Defined | 0.450515 | 0.364065 | Fraction | Calculated conversion; no maintenance/growth capex split |
| Undrawn revolving borrowings available | 843 | Not supplied: prior-year availability not extracted | US$m | Reported FY2024 net of letters of credit; Annual page:59 |
| Additional receivables-facility availability | 162.5 | Not supplied: prior-year availability not extracted | US$m | Reported FY2024; borrowing-base and draw conditions unverified; Annual page:62 |
| Cash plus reported undrawn revolver | 7,104 | Not calculable: prior-year availability not extracted | US$m | Calculated static subtotal, not unrestricted liquidity |
| Cash plus revolver and receivables availability | 7,266.5 | Not calculable: prior-year availability not extracted | US$m | Calculated conditional envelope; no double-counting of the receivables facility |
| Dividends payable | 4,216 | — (reported dash) | US$m | Reported liability; Annual page:120; not yet a FY2024 cash outflow |
| Declared dividend and associated equivalent payment | 4,348 | Not supplied: no comparable event amount selected | US$m | Calculated FY2024 accrual-linked event; Annual page:63 |
| Cash after that payment only | 1,913 | Not calculable: no comparable event selected | US$m | Static calculated illustration, not a forecast or subsequent actual balance |

### Chart data: leverage

| Period | Total debt / EBITDA | Net debt / EBITDA | Reporting unit | Basis and limitation |
| --- | --- | --- | --- | --- |
| FY2023 / 2023-09-30 | 6.33 | 5.22 | x | Gross principal including finance leases and rounded receivables debt / issuer-reported EBITDA 3,148; net debt deducts consolidated cash. Not covenant leverage. Annual pages 71, 120, 145. |
| FY2024 / 2024-09-30 | 6.57 | 4.93 | x | Gross principal including finance leases and rounded receivables debt / issuer-reported EBITDA 3,813; cash precedes accrued shareholder payment. Not covenant leverage. Annual pages 63, 71, 120, 144-145. |

### Chart data: interest cover

| Period | EBITDA / cash interest | Reporting unit | Basis and limitation |
| --- | --- | --- | --- |
| FY2023 | 2.71 | x | EBITDA 3,148 / cash interest paid, net 1,160. Gross cash-interest coverage is Not calculable: gross cash interest not separately supplied in retained evidence. Annual pages 71, 123. |
| FY2024 | 3.29 | x | EBITDA 3,813 / cash interest paid, net 1,158. Net-interest proxy, not gross cash-interest or covenant coverage. Annual pages 71, 123. |

### Chart data: liquidity

| Period | Cash | Undrawn committed facilities | Reporting unit | Basis and limitation |
| --- | --- | --- | --- | --- |
| 2023-09-30 | 3472 | Not supplied: prior-year facility availability not extracted | US$m | Reported consolidated cash; no unrestricted-cash certification or historical undrawn-facility reconstruction. Annual page:120. |
| 2024-09-30 | 6261 | 843 | US$m | Reported revolving borrowings available after 67 of letters of credit; excludes conditional receivables availability 162.5. Cash precedes accrued shareholder settlement; draw conditions unverified. Annual pages 59, 62-63, 120. |

### Chart data: debt maturities

| Period | Debt maturing | Reporting unit | Basis and limitation |
| --- | --- | --- | --- |
| FY2025 | 93 | US$m | Reported long-term principal schedule only; excludes short-term receivables financing and finance leases. Receivables draw 487.5 matures July 11, 2025 absent extension. Annual pages 62, 153. |
| FY2026 | 92 | US$m | Reported long-term principal schedule; excludes finance leases and short-term receivables facility. Annual page:153. |
| FY2027 | 92 | US$m | Reported long-term principal schedule; excludes finance leases and short-term receivables facility. Annual page:153. |
| FY2028 | 6637 | US$m | Fiscal-year bucket, not calendar year; includes November 15, 2027 note maturity; excludes finance leases. Annual pages 59, 153. |
| FY2029 | 4768 | US$m | Reported long-term principal schedule; excludes finance leases and short-term receivables facility. Annual page:153. |
| Thereafter | 12637 | US$m | Reported aggregate; no invented annual allocation; excludes finance leases. Annual page:153. |

### Reported income statement

Amounts are US$m, except the expressly separated per-share and share-count rows. Source: Annual page:121, including the contiguous labels “SELLING AND ADMINISTRATIVE EXPENSES”, “AMORTIZATION OF INTANGIBLE ASSETS” and “INCOME FROM OPERATIONS”. Expense rows below retain printed positive outflow magnitudes; they are deducted in calculations. The negative OTHER row is a printed expense credit, not an additional expense. Values are reported, not synthesized subtotals.

| Source label | FY2024 | FY2023 | Quantity and sign presentation |
| --- | --- | --- | --- |
| NET SALES | 7,940 | 6,585 | Money; positive income |
| COST OF SALES | 3,268 | 2,743 | Money; outflow magnitude |
| GROSS PROFIT | 4,672 | 3,842 | Money; positive subtotal |
| SELLING AND ADMINISTRATIVE EXPENSES | 980 | 780 | Money; outflow magnitude |
| AMORTIZATION OF INTANGIBLE ASSETS | 161 | 139 | Money; outflow magnitude |
| INCOME FROM OPERATIONS | 3,531 | 2,923 | Money; positive subtotal |
| INTEREST EXPENSE—NET | 1,286 | 1,164 | Money; net expense magnitude |
| REFINANCING COSTS | 58 | 56 | Money; outflow magnitude |
| OTHER (INCOME) EXPENSE | -28 | -13 | Money; signed expense credit |
| INCOME FROM CONTINUING OPERATIONS BEFORE INCOME TAXES | 2,215 | 1,716 | Money; positive subtotal |
| INCOME TAX PROVISION | 500 | 417 | Money; expense magnitude |
| INCOME FROM CONTINUING OPERATIONS | 1,715 | 1,299 | Money; positive income |
| INCOME FROM DISCONTINUED OPERATIONS, NET OF TAX | — (reported dash) | — (reported dash) | Money; no amount printed |
| NET INCOME | 1,715 | 1,299 | Money; consolidated income |
| LESS: NET INCOME ATTRIBUTABLE TO NONCONTROLLING INTERESTS | -1 | -1 | Money; signed deduction |
| NET INCOME ATTRIBUTABLE TO TD GROUP | 1,714 | 1,298 | Money; parent-attributable income |
| NET INCOME APPLICABLE TO TD GROUP COMMON STOCKHOLDERS | 1,481 | 1,260 | Money; separate shareholder measure |
| Earnings per share from continuing operations—basic and diluted | 25.62 | 22.03 | USD/share, not US$m |
| Earnings per share from discontinued operations—basic and diluted | — (reported dash) | — (reported dash) | USD/share |
| Earnings per share | 25.62 | 22.03 | USD/share |
| Cash dividends declared per common share | 110.00 | — (reported dash) | USD/share; declaration, not cash paid |
| Basic and diluted | 57.8 | 57.2 | Weighted-average shares, millions; not money |

### Reported balance sheet

Source: Annual page:120; PDF page:105 is a matching alternate text sample. All rows are signed US$m. The equity share-count annotations are retained separately below, not mixed into monetary amounts.

| Source label | 2024-09-30 | 2023-09-30 |
| --- | --- | --- |
| Cash and cash equivalents | 6,261 | 3,472 |
| Trade accounts receivable—Net | 1,381 | 1,230 |
| Inventories—Net | 1,876 | 1,616 |
| Prepaid expenses and other | 511 | 420 |
| Total current assets | 10,029 | 6,738 |
| PROPERTY, PLANT AND EQUIPMENT—NET | 1,488 | 1,255 |
| GOODWILL | 10,419 | 8,988 |
| OTHER INTANGIBLE ASSETS—NET | 3,446 | 2,747 |
| OTHER NON-CURRENT ASSETS | 204 | 242 |
| TOTAL ASSETS | 25,586 | 19,970 |
| Current portion of long-term debt | 98 | 71 |
| Short-term borrowings—trade receivable securitization facility | 486 | 349 |
| Accounts payable | 323 | 305 |
| Dividends payable | 4,216 | — (reported dash) |
| Accrued and other current liabilities | 1,216 | 854 |
| Total current liabilities | 6,339 | 1,579 |
| LONG-TERM DEBT | 24,296 | 19,330 |
| DEFERRED INCOME TAXES | 766 | 627 |
| OTHER NON-CURRENT LIABILITIES | 468 | 412 |
| Total liabilities | 31,869 | 21,948 |
| Common stock - $.01 par value; authorized 224,400,000 shares; issued 61,904,833 and 60,995,513 at September 30, 2024 and September 30, 2023, respectively | 1 | 1 |
| Additional paid-in capital | 2,819 | 2,440 |
| Accumulated deficit | -7,362 | -2,621 |
| Accumulated other comprehensive loss | -42 | -98 |
| Treasury stock, at cost; 5,688,639 shares at September 30, 2024 and September 30, 2023, respectively | -1,706 | -1,706 |
| Total TD Group stockholders’ deficit | -6,290 | -1,984 |
| NONCONTROLLING INTERESTS | 7 | 6 |
| Total stockholders’ deficit | -6,283 | -1,978 |
| TOTAL LIABILITIES AND STOCKHOLDERS’ DEFICIT | 25,586 | 19,970 |

The long common-stock label contains actual share counts and USD par value, not additional money observations. The authorized and issued share counts and treasury-share counts remain distinct from the monetary carrying values. No restricted-cash row is printed in this annual balance sheet; that is not a certification that all cash is unrestricted or accessible to debt issuers.

### Reported cash-flow statement

All values are signed US$m. Sources: Annual page:122 for operating reconciliation through deferred taxes; page:123 for the continuation, investing, financing and supplemental disclosures. Dashes retain the source presentation. Supplemental cash-paid rows are positive outflow magnitudes, not financing proceeds.

| Source label | FY2024 | FY2023 | Presentation / locator |
| --- | --- | --- | --- |
| Net income | 1,715 | 1,299 | Signed; page:122 |
| Income from discontinued operations, net of tax | — (reported dash) | — (reported dash) | page:122 |
| Depreciation | 149 | 129 | Signed adjustment; page:122 |
| Amortization of intangible assets and product certification costs | 163 | 139 | Signed adjustment; page:122 |
| Amortization of debt issuance costs, original issue discount and premium | 40 | 41 | Signed adjustment; page:122 |
| Amortization of inventory step-up | 21 | 2 | Signed adjustment; page:122 |
| Amortization of loss contract reserves | -35 | -34 | Signed adjustment; page:122 |
| Refinancing costs | 58 | 56 | Signed adjustment; page:122 |
| Gain on sale of businesses, net | -11 | — (reported dash) | Signed adjustment; page:122 |
| Non-cash stock and deferred compensation expense | 217 | 157 | Signed adjustment; page:122 |
| Deferred income taxes | 10 | 3 | Signed adjustment; page:122 |
| Foreign currency exchange losses (gains) | 20 | 14 | Signed adjustment; page:123 |
| (Gain) loss on settlement of the Esterline Retirement Plan (the “ERP”) | — (reported dash) | -9 | Signed adjustment; page:123 |
| Cash refund (contribution) for the ERP settlement, net | — (reported dash) | 9 | Signed refund/inflow; not recast as negative cash tax or expense; page:123 |
| Trade accounts receivable | -84 | -212 | Asset/liability change; page:123 |
| Inventories | -104 | -261 | Asset/liability change; page:123 |
| Income taxes (receivable) payable | -62 | 168 | Asset/liability change; page:123 |
| Other assets | -60 | -44 | Asset/liability change; page:123 |
| Accounts payable | -11 | 12 | Asset/liability change; page:123 |
| Accrued interest | 60 | -45 | Asset/liability change; page:123 |
| Accrued and other liabilities | -41 | -49 | Asset/liability change; page:123 |
| Net cash provided by operating activities | 2,045 | 1,375 | Reported subtotal; page:123 |
| Capital expenditures | -165 | -139 | Signed outflow; page:123 |
| Acquisition of businesses, net of cash acquired | -2,347 | -762 | Signed outflow; page:123 |
| Other investing transactions | 71 | 1 | Signed inflow; page:123 |
| Net cash used in investing activities | -2,441 | -900 | Reported subtotal; page:123 |
| Proceeds from exercise of stock options | 245 | 215 | Signed inflow; page:123 |
| Dividends and dividend equivalent payments | -2,038 | -38 | Signed outflow; page:123 |
| Repurchases of common stock | — (reported dash) | — (reported dash) | page:123 |
| Proceeds from issuance of senior secured notes, net | 7,373 | 3,504 | Signed inflow; page:123 |
| Repayments of senior secured notes | -4,400 | -1,122 | Signed outflow; page:123 |
| Repayments of senior subordinated notes, net | -550 | -1,459 | Signed outflow; page:123 |
| Repayment on revolving credit facility | — (reported dash) | — (reported dash) | page:123 |
| Proceeds from trade receivable securitization facility, net | 137 | — (reported dash) | Signed inflow; page:123 |
| Proceeds from term loans, net | 6,815 | 6,238 | Signed inflow; page:123 |
| Repayment on term loans | -4,403 | -7,334 | Signed outflow; page:123 |
| Financing costs and other, net | -8 | -20 | Signed outflow; page:123 |
| Net cash provided by (used in) financing activities | 3,171 | -16 | Reported subtotal; page:123 |
| EFFECT OF EXCHANGE RATE CHANGES ON CASH AND CASH EQUIVALENTS | 14 | 12 | Signed movement; page:123 |
| NET INCREASE (DECREASE) IN CASH AND CASH EQUIVALENTS | 2,789 | 471 | Reported movement; page:123 |
| CASH AND CASH EQUIVALENTS, BEGINNING OF PERIOD | 3,472 | 3,001 | Reported opening cash; page:123 |
| CASH AND CASH EQUIVALENTS, END OF PERIOD | 6,261 | 3,472 | Reported closing cash; page:123 |
| Cash paid during the period for interest, net | 1,158 | 1,160 | Outflow magnitude; page:123 |
| Cash paid during the period for income taxes, net of refunds | 539 | 260 | Outflow magnitude; page:123 |

### Reported non-GAAP definitions and adjustment register

Annual page:71 prints the following complete net-income-to-EBITDA bridge. The positive adjustments are additions to income, not a second presentation of signed income-statement expenses. Annual page:70 warns that EBITDA As Defined “excludes the cash expense we have incurred to integrate acquired businesses into our operations”. Therefore adjusted earnings are not automatically discretionary cash.

| Reported bridge label | FY2024 | FY2023 | US$m; classification and definition |
| --- | --- | --- | --- |
| Net Income | 1,715 | 1,299 | GAAP consolidated starting point |
| Depreciation and amortization expense | 312 | 268 | Noncash expense adjustment; not merely intangible amortization |
| Interest expense-net | 1,286 | 1,164 | Net financing adjustment |
| Income tax provision | 500 | 417 | Tax adjustment |
| EBITDA | 3,813 | 3,148 | Reported non-GAAP subtotal |
| Acquisition transaction and integration-related expenses (1) | 70 | 18 | Integration/relocation, deal/valuation costs and inventory step-up amortization; mixed cash/noncash; item-level split Not supplied |
| Non-cash stock and deferred compensation expense (2) | 217 | 157 | Incentive and deferred compensation plans; recurring economic compensation risk despite reported noncash label |
| Refinancing costs (3) | 58 | 56 | Issuance, extinguishment, refinancing and amendment expense; recurrence cannot be dismissed after inclusion in both periods |
| Other, net (4) | 15 | 16 | Currency transactions, payroll withholding related to equivalents/options, pension, deferred compensation and miscellaneous items; heterogeneous adjustment |
| EBITDA As Defined | 4,173 | 3,395 | Management-adjusted, not independently underwritten or legally certified |

### Reported segments

All amounts US$m; Annual page:49 sales and page:50 EBITDA As Defined. Each operating segment is allocated once; corporate is a reconciliation deduction, not another revenue segment.

| Segment / reconciliation label | FY2024 sales | FY2023 sales | FY2024 EBITDA As Defined | FY2023 EBITDA As Defined | Basis |
| --- | --- | --- | --- | --- | --- |
| Power & Control | 3,941 | 3,316 | 2,236 | 1,866 | Reported operating segment |
| Airframe | 3,809 | 3,094 | 1,962 | 1,547 | Reported operating segment |
| Non-aviation | 190 | 175 | 81 | 71 | Reported operating segment |
| Total segment EBITDA As Defined | Not supplied: no separate sales row with this label | Not supplied: no separate sales row with this label | 4,279 | 3,484 | Reported profit subtotal, not consolidated profit |
| Less: Unallocated corporate EBITDA As Defined | Not supplied: corporate sales not reported | Not supplied: corporate sales not reported | 106 | 89 | Printed deduction magnitude |
| Net sales / Total Company EBITDA As Defined | 7,940 | 6,585 | 4,173 | 3,395 | Two explicitly reported consolidated totals, not a new segment |

Acquisition contribution uses management's convention: Annual page:50 says acquisition sales cover “the period up to one year from the respective acquisition date.” This is not a fully comparable constant-perimeter earnings series.

### Reported debt and facility register

All principal/carrying values US$m. Annual pages 144-145 distinguish gross principal from debt issuance costs and original issue discount/premium. Rates are percentages; floating margins below are basis points. Facility descriptions are issuer summaries, not operative agreements.

| Instrument / reported row | FY2024 gross | FY2024 net carrying | FY2023 gross | FY2023 net carrying | Maturity / rate / source |
| --- | --- | --- | --- | --- | --- |
| Short-term borrowings—trade receivable securitization facility | 487 | 486 | 350 | 349 | Annual pages 144-145, rounded debt table; July 11, 2025; Term SOFR + 145 bps in FY2024 summary page:62 |
| Term loans | 8,702 | 8,642 | 6,249 | 6,179 | Four current tranches below; Annual pages 59, 145 |
| 6.25% secured notes due 2026 | — (not outstanding in current table) | — (not outstanding in current table) | 4,400 | 4,377 | Annual page:145; no current debt assumed |
| 7.50% senior subordinated notes due 2027 | — (not outstanding in current table) | — (not outstanding in current table) | 550 | 548 | Annual page:145; no current debt assumed |
| 5.50% senior subordinated notes due 2027 | 2,650 | 2,641 | 2,650 | 2,638 | November 15, 2027; 5.50%; Annual pages 59, 145 |
| 6.75% secured notes due 2028 | 2,100 | 2,077 | 2,100 | 2,071 | August 15, 2028; 6.75%; Annual pages 59, 145 |
| 4.625% senior subordinated notes due 2029 | 1,200 | 1,194 | 1,200 | 1,193 | January 15, 2029; 4.625%; Annual pages 59, 145 |
| 6.375% secured notes due 2029 | 2,750 | 2,727 | — (not outstanding in prior table) | — (not outstanding in prior table) | March 1, 2029; 6.375%; Annual pages 59, 145 |
| 4.875% senior subordinated notes due 2029 | 750 | 746 | 750 | 745 | May 1, 2029; 4.875%; Annual pages 60, 145 |
| 6.875% secured notes due 2030 | 1,450 | 1,438 | 1,450 | 1,436 | December 15, 2030; 6.875%; Annual pages 60, 145 |
| 7.125% secured notes due 2031 | 1,000 | 984 | — (not outstanding in prior table) | — (not outstanding in prior table) | December 1, 2031; 7.125%; Annual pages 60, 145 |
| 6.625% secured notes due 2032 | 2,200 | 2,180 | — (not outstanding in prior table) | — (not outstanding in prior table) | March 1, 2032; 6.625%; Annual pages 60, 145 |
| 6.00% secured notes due 2033 | 1,500 | 1,486 | — (not outstanding in prior table) | — (not outstanding in prior table) | January 15, 2033; 6.00%; Annual pages 60, 145 |
| Government refundable advances | 17 | 17 | 21 | 21 | Included in debt, not recast as grant income; Annual page:145 |
| Finance lease obligations | 262 | 262 | 193 | 193 | Included in debt; Annual page:145 |
| Unlabelled long-term-debt subtotal before current portion | 24,581 | 24,394 | 19,563 | 19,401 | Reported subtotal excludes the separately printed short-term receivables row; Annual page:145 |
| Less: current portion | 99 | 98 | 71 | 71 | Printed deduction; Annual page:145 |
| Long-term debt | 24,482 | 24,296 | 19,492 | 19,330 | After current-portion deduction; Annual page:145 |

Annual page:145 also prints total long-term debt issuance costs of -136 and original issue discount/premium of -51 for FY2024, and -106 and -56 for FY2023. Short-term receivables debt has issuance costs of -1 in each year. These accounting deductions explain the gross/carrying bridge; they do not reduce contractual principal.

| FY2024 facility / tranche | Principal or commitment, US$m | Maturity | Rate / availability | Evidence and limitation |
| --- | --- | --- | --- | --- |
| Tranche I | 1,871 | 2028-08-24 | Term SOFR + 275 bps | Annual page:59; fully drawn term loans |
| Tranche J | 3,632 | 2031-02-28 | Term SOFR + 250 bps | Annual page:59 |
| Tranche K | 1,699 | 2030-03-22 | Term SOFR + 275 bps | Annual page:59 |
| Tranche L | 1,500 | 2032-01-19 | Term SOFR + 250 bps | Annual page:59 |
| Revolving credit facility | 910 commitment | 2029-02-27 | Term SOFR + 225 bps; 843 borrowings available; 67 letters of credit | Annual page:59; up to 139 multicurrency; unused fee 0.5% per annum; no term-loan SOFR floor reported |
| Securitization Facility | 650 capacity | 2025-07-11 | 487.5 drawn; 162.5 available; Term SOFR + 145 bps | Annual page:62; collateralized by substantially all domestic operations' trade receivables, page:63; annual extension conditional on no termination events |

The 487 gross receivables figure in the debt table and 487.5 in the facility narrative are retained with their distinct published precision. No silent replacement is made. Canonical debt ratios consistently use the rounded debt table; facility availability and the separate near-term illustration use the facility narrative. The reported 24,319 long-term maturity total plus finance leases 262 reconciles to gross long-term debt 24,581; adding rounded receivables debt 487 gives 25,068. Thus the chart is intentionally not a complete all-debt cash-use schedule.

### Non-debt liabilities and funding review

Every balance-sheet row in the retained annual statement was reviewed for funding implications; assets and equity are not classified as funding liabilities. Long-term debt is a debt row, not a non-debt funding story. Deferred taxes and other non-current liabilities are retained as reported, without assuming immediate cash settlement or complete note decomposition.

| Liability detail / story | FY2024 | FY2023 | Mechanic and credit implication | Source |
| --- | --- | --- | --- | --- |
| Dividends payable | 4,216 | — (reported dash) | Material declared shareholder claim against apparent cash; payment timing must be separated from FY2024 cash flows. | Annual page:120 |
| Compensation and related benefits | 256 | 217 | Operating accrual, not additional undrawn funding capacity. | Annual page:144 |
| Interest | 185 | 125 | Financing accrual; cash-interest timing differs from income-statement expense. | Annual page:144 |
| Dividend equivalent payments, current (Note 16) | 180 | 19 | Additional shareholder/option-holder-linked cash claims; only the specifically associated 132 is used in the declared-payment illustration. | Annual pages 144, 63 |
| Contract liabilities, current (Note 3) | 168 | 79 | Customer-funded operating liability; performance obligations remain, so not free cash or financial debt by default. | Annual page:144 |
| Income taxes payable, current | 108 | 138 | Tax settlement claim; not debt principal. | Annual page:144 |
| Loss contract reserves | 50 | 42 | Future contract-cost exposure; amortization is separately included in CFO reconciliation. | Annual pages 144, 122 |
| Product warranties | 36 | 28 | Operating claim; precise settlement timing Not supplied. | Annual page:144 |
| Environmental and other litigation reserves | 27 | 16 | Contingent operating/legal cash exposure; reserve adequacy not assessed. | Annual page:144 |
| Current operating lease liabilities (Note 17) | 19 | 16 | Lease claim excluded from primary debt definition; not confused with undiscounted lease cash payments. | Annual page:144 |
| Foreign currency forward exchange contracts (Note 19) | 1 | 5 | Derivative liability, not a borrowing commitment. | Annual page:144 |
| Other | 186 | 169 | Residual liability detail; composition and timing remain a gap, not assumed immaterial. | Annual page:144 |
| Accrued and other current liabilities | 1,216 | 854 | Reported total; components above must not be added again to total liabilities. | Annual page:144 |
| DEFERRED INCOME TAXES | 766 | 627 | Timing-related accounting liability; full reversal/cash schedule Not supplied. | Annual page:120 |
| OTHER NON-CURRENT LIABILITIES | 468 | 412 | Aggregate retained; precise funding-like components and settlement profile not fully extracted. | Annual page:120 |

**Accrual-linked event, not a FY2024 payment:** Annual page:63 states the October 18, 2024 special dividend of 4,216 and associated equivalent payment of 132 were “both of which are accrued as of September 30, 2024.” Combined, 4,348 of the reported cash balance is connected to this declared event. Deducting it solely for illustration leaves cash of 1,913, before any other subsequent cash flows. This is neither an unrestricted-cash certification nor the actual October cash balance. Do not subtract all 180 of current equivalents and also subtract the associated 132: that would double count part of the same liability.

**Separately tagged subsequent financing:** Annual page:63 states, “On October 16, 2024, the Company drew the remaining $162.5 million available under the Securitization Facility.” This is not included in September debt, cash or FY2024 financing cash flows, and is not added to period-end liquidity as both drawn cash and undrawn availability.

### Evidence-based credit interpretation

**Leverage — calculated facts, then interpretation.** Gross debt / reported EBITDA increased from 6.33x to 6.57x, even as net debt / reported EBITDA declined from 5.22x to 4.93x. Gross debt was 19,913 and 25,068, respectively, while cash was 3,472 and 6,261. Therefore the improvement in the net metric is not gross deleveraging. Cash netting is especially fragile because of the separately accrued 4,348 payment. Credit implication: use both gross and net leverage; do not infer equivalent covenant headroom or durable debt reduction from the net ratio alone. Evidence: Annual pages 63, 71, 120, 144-145; calculated bridge below. Confidence High for the accounting-based comparison, limited for accessible cash and legal leverage.

**Coverage — better service capacity, qualified denominator.** Reported EBITDA / cash interest paid, net improved from 2.71x to 3.29x as EBITDA increased and net interest paid was 1,160 versus 1,158. This supports improved historical cash debt-service capacity, not a claim of gross interest coverage or forward protection against rates. Net income-based EBITDA retains refinancing and other non-operating effects; adjusted coverage of 2.93x and 3.60x is a separate, more favorable sensitivity. Evidence: Annual pages 71, 123. Confidence High for the net-interest proxy; gross interest coverage is Not calculable from retained evidence.

**Cash-flow quality — stronger conversion but competing uses consumed it.** CFO increased from 1,375 to 2,045; free cash flow after capex increased from 1,236 to 1,880. CFO / EBITDA As Defined improved from 0.405007 to 0.490055. However, FY2024 acquisitions of 2,347 and cash dividends/equivalents of 2,038 left a calculated deficit of -2,505 after free cash flow, before other investing and financing flows. The corresponding FY2023 residual was positive 436. Reported FY2024 net financing inflow of 3,171 helps explain why cash rose despite that funding deficit. Credit implication: internal cash generation improved but did not fund the combination of acquisition spending and shareholder distributions. These residuals do not assert that any specific borrowing was legally earmarked to a distribution. Evidence: Annual pages 122-123; calculations below. Confidence High.

**Liquidity — large static cash, material pre-committed use and facility conditions.** Cash plus available revolver is 7,104; including separately reported receivables availability gives a conditional envelope of 7,266.5. Neither amount is an unrestricted cash-runway estimate. The shareholder claim, cash held outside the relevant borrowing group, receivables eligibility and draw conditions can reduce usable liquidity. The FY2025 published long-term maturity bucket of 93 excludes the 487.5 receivables facility maturing in July 2025; those two items alone total 580.5 before finance leases. Annual page:172 separately reports finance lease payments of 20 in FY2025, an undiscounted interest-inclusive amount that must not be added to principal debt totals as though wholly principal. Credit implication: exact monthly runway remains restricted, and renewal of short-term receivables funding matters despite a small published long-term bucket. Confidence High for reported balances and exclusions, Medium for the conditional liquidity envelope.

**Definitions — adjusted earnings are not a substitute for accounting or legal analysis.** The management bridge adds 360 in FY2024 and 247 in FY2023 beyond reported EBITDA, including integration costs, compensation and refinancing costs. This changes gross leverage to 6.01x and 5.87x, respectively, but no item-level cash split, recurrence test or lender eligibility has been established. Operating income plus total D&A produces 3,843 and 3,191 rather than reported EBITDA of 3,813 and 3,148: these are different definitions, not an extraction conflict. Total D&A must not replace the 161/139 intangible amortization row in the operating-expense block. Credit implication: retain both earnings definitions and reserve adjustment acceptance for the earnings-quality review. Confidence Medium on economic sustainability.

**Legal and reporting quality — usable statements, bounded conclusions.** Annual page:124 establishes consolidated U.S. GAAP reporting, while page:153 identifies TransDigm Inc. notes and guarantee descriptions. This does not establish borrower-accessible consolidated cash or complete instrument-specific collateral rights. Annual page:62 describes a revolver-triggered net-debt leverage test; page:70 describes secured indebtedness against Consolidated EBITDA. Those descriptions are not reconciled here. Management's compliance statement in page:62 is retained as management language, not independently calculated compliance. Operative covenant ratio, headroom and capacity are Not calculable without the executed definitions and amendment chain. No agency, market or other external evidence is used.

## Calculations

### Calculation conventions and lineage

All new arithmetic was executed with the Decimal-38 calculate kernel. Amounts below are US$m, with the consolidated entity/perimeter and exact FY flow dates or balance-sheet instants specified above. Ratios are fractions until presented as x; no percentage conversion is implied by a fractional conversion metric. Ratios displayed as x are rounded to two decimals; margin and conversion fractions are rounded to six decimals. Unrounded kernel outputs remain the calculation basis. Calculations do not increase the precision of the underlying rounded statements.

### Income statement and expense-block reconciliation — calculated, not reported aggregates

| Calculation | FY2024 formula and result | FY2023 formula and result | Source components and limitation |
| --- | --- | --- | --- |
| Gross profit check | 7,940 - 3,268 - 4,672 = 0 residual | 6,585 - 2,743 - 3,842 = 0 residual | Annual page:121; cost of sales is above gross profit |
| Complete expense block below gross profit | 980 + 161 = 1,141 | 780 + 139 = 919 | Annual page:121; calculated S&A plus intangible amortization, not a source-printed opex subtotal |
| Operating profit check | 4,672 - 980 - 161 - 3,531 = 0 residual | 3,842 - 780 - 139 - 2,923 = 0 residual | Annual page:121; does not subtract total D&A again |
| Pretax income check | 3,531 - 1,286 - 58 + 28 - 2,215 = 0 residual | 2,923 - 1,164 - 56 + 13 - 1,716 = 0 residual | Annual page:121; printed negative OTHER expense adds income |
| Continuing income check | 2,215 - 500 - 1,715 = 0 residual | 1,716 - 417 - 1,299 = 0 residual | Annual page:121 |
| Reported EBITDA reproduction | 1,715 + 312 + 1,286 + 500 = 3,813 | 1,299 + 268 + 1,164 + 417 = 3,148 | Annual page:71; retains issuer definition |
| Adjusted EBITDA reproduction | 3,813 + 70 + 217 + 58 + 15 = 4,173 | 3,148 + 18 + 157 + 56 + 16 = 3,395 | Annual page:71; no validation of adjustment quality |
| Total incremental adjustments | 4,173 - 3,813 = 360 | 3,395 - 3,148 = 247 | Annual page:71 |
| Operating-income-plus-D&A diagnostic | 3,531 + 312 = 3,843 | 2,923 + 268 = 3,191 | Annual pages 121, 71; alternative diagnostic, not reported EBITDA |
| Difference from issuer EBITDA | 3,843 - 3,813 = 30 | 3,191 - 3,148 = 43 | Net refinancing/other non-operating effects; not unresolved numerical error |
| Operating margin | 3,531 / 7,940 = 0.444710 | 2,923 / 6,585 = 0.443888 | Annual page:121 |

### Cash-flow bridges — calculated

| Calculation | FY2024 formula and result | FY2023 formula and result | Evidence and limitation |
| --- | --- | --- | --- |
| CFO reconciliation, nonzero printed operands | 1,715 + 149 + 163 + 40 + 21 - 35 + 58 - 11 + 217 + 10 + 20 - 84 - 104 - 62 - 60 - 11 + 60 - 41 = 2,045 | 1,299 + 129 + 139 + 41 + 2 - 34 + 56 + 157 + 3 + 14 - 9 + 9 - 212 - 261 + 168 - 44 + 12 - 45 - 49 = 1,375 | Annual pages 122-123; source dashes omitted, not unknown operands assumed zero; reproduced reported CFO |
| Management CFO-to-EBITDA bridge | 2,045 + 272 + 1,246 + 490 + 35 - 217 - 58 = 3,813 | 1,375 + 415 + 1,123 + 414 + 34 - 157 - 56 = 3,148 | Every component is separately printed in Annual page:71; 1,246/1,123 excludes debt-cost amortization and is not cash interest paid |
| Levered FCF | 2,045 - 165 = 1,880 | 1,375 - 139 = 1,236 | Annual page:123; CFO already includes cash interest and tax; before acquisitions and dividends |
| Residual after acquisitions and cash distributions | 1,880 - 2,347 - 2,038 = -2,505 | 1,236 - 762 - 38 = 436 | Annual page:123; excludes other investing, options proceeds and debt flows |
| Net cash movement | 2,045 - 2,441 + 3,171 + 14 = 2,789 | 1,375 - 900 - 16 + 12 = 471 | Annual page:123; agrees with reported movement and opening/closing cash |
| CFO conversion | 2,045 / 4,173 = 0.490055 | 1,375 / 3,395 = 0.405007 | Annual pages 71, 123 |
| FCF conversion | 1,880 / 4,173 = 0.450515 | 1,236 / 3,395 = 0.364065 | FCF calculated above; adjusted denominator remains unvalidated |

### Balance-sheet, debt and segment bridges — calculated

| Calculation | FY2024 / current instant | FY2023 / prior instant | Evidence and limitation |
| --- | --- | --- | --- |
| Asset subtotal check | 10,029 + 1,488 + 10,419 + 3,446 + 204 - 25,586 = 0 | 6,738 + 1,255 + 8,988 + 2,747 + 242 - 19,970 = 0 | Annual page:120; zero is a reconciliation residual |
| Liability subtotal check | 6,339 + 24,296 + 766 + 468 - 31,869 = 0 | 1,579 + 19,330 + 627 + 412 - 21,948 = 0 | Annual page:120 |
| Balance-sheet equation check | 31,869 - 6,283 - 25,586 = 0 | 21,948 - 1,978 - 19,970 = 0 | Annual page:120; uses total equity including noncontrolling interests |
| Carrying debt | 98 + 486 + 24,296 = 24,880 | 71 + 349 + 19,330 = 19,750 | Annual page:120; includes current portion once |
| Gross debt | 24,581 + 487 = 25,068 | 19,563 + 350 = 19,913 | Annual pages 144-145; complete long-term subtotal plus separate short-term facility |
| Gross less carrying debt | 25,068 - 24,880 = 188 | 19,913 - 19,750 = 163 | Debt issuance costs and discount/premium bridge; not principal repayment |
| Net debt | 25,068 - 6,261 = 18,807 | 19,913 - 3,472 = 16,441 | Annual pages 120, 144-145; consolidated cash deducted without accessibility adjustment |
| Maturity schedule sum | 93 + 92 + 92 + 6,637 + 4,768 + 12,637 = 24,319 | Not calculated: historical maturity schedule not selected | Annual page:153; excludes finance leases and receivables debt |
| Maturity-to-total-debt bridge | 24,319 + 262 + 487 = 25,068 | Not calculated: historical maturity schedule not selected | Annual pages 145, 153; rounded principal basis |
| Segment sales check | 3,941 + 3,809 + 190 = 7,940 | 3,316 + 3,094 + 175 = 6,585 | Annual page:49 |
| Segment adjusted earnings check | 2,236 + 1,962 + 81 - 106 = 4,173 | 1,866 + 1,547 + 71 - 89 = 3,395 | Annual page:50; corporate deduction included once |

### Ratio calculation register — calculated

| Metric | FY2024 operands and result | FY2023 operands and result | Component lineage |
| --- | --- | --- | --- |
| Gross debt / EBITDA | 25,068 / 3,813 = 6.57x | 19,913 / 3,148 = 6.33x | Gross debt bridge; reported EBITDA Annual page:71 |
| Net debt / EBITDA | 18,807 / 3,813 = 4.93x | 16,441 / 3,148 = 5.22x | Net debt bridge; Annual page:71 |
| Gross debt / EBITDA As Defined | 25,068 / 4,173 = 6.01x | 19,913 / 3,395 = 5.87x | Gross debt bridge; Annual page:71 |
| Net debt / EBITDA As Defined | 18,807 / 4,173 = 4.51x | 16,441 / 3,395 = 4.84x | Net debt bridge; Annual page:71 |
| EBITDA / net cash interest | 3,813 / 1,158 = 3.29x | 3,148 / 1,160 = 2.71x | Annual pages 71, 123; net-interest proxy |
| EBITDA As Defined / net cash interest | 4,173 / 1,158 = 3.60x | 3,395 / 1,160 = 2.93x | Annual pages 71, 123; adjusted net-interest proxy |

### Static liquidity/event calculations — calculated, not forecasts

| Calculation | Formula and result, US$m | Date, source and restriction |
| --- | --- | --- |
| Cash plus revolver | 6,261 + 843 = 7,104 | 2024-09-30; Annual pages 120, 59; no cash-access certification |
| Total separately reported undrawn availability | 843 + 162.5 = 1,005.5 | 2024-09-30; Annual pages 59, 62; includes conditional receivables availability |
| Conditional liquidity envelope | 6,261 + 843 + 162.5 = 7,266.5 | Same instant; do not treat as unconditional committed revolver capacity |
| Accrual-linked declared payment | 4,216 + 132 = 4,348 | September declaration, settled October 18, 2024; Annual page:63 |
| Cash after only that use | 6,261 - 4,216 - 132 = 1,913 | Illustration from period-end cash; excludes subsequent draw and all other cash flows |
| FY2025 long-term maturity plus narrative receivables principal | 93 + 487.5 = 580.5 | Annual pages 153, 62; narrative facility precision, excludes finance lease principal and interest |

## Gaps

### Consolidated actionable register

| Underlying issue | Affected quantities, periods and recipients | Assessment and required action |
| --- | --- | --- |
| Information cutoff and source integrity | Every annual conclusion for FY2024/FY2023; all consumers | Source identity and pinned hashes are available; full preparation/fidelity manifest is not. Annual audit date postdates as-of. Clarify retrospective versus strict contemporaneous use and obtain preparation/coverage records. Retrospective facts can be used with limitations; no information-at-date certification. |
| Unrestricted cash and facility access | Cash 6,261; revolver 843; receivables availability 162.5; liquidity envelope 7,266.5 at 2024-09-30; liquidity, stress and forward-model consumers | Annual pages 59, 62-63, 120 establish reported values, not cash-by-entity or draw eligibility. Obtain cash restrictions/entity balances, borrowing base, draw conditions and monthly uses. No precise runway or fully available liquidity conclusion. |
| Operative legal definitions and entity boundary | All covenant ratios, compliance, baskets, secured debt definitions, guarantees and recovery; legal, refinancing, recovery, stress and forward-model consumers | Annual pages 62 and 70 differ in covenant numerator descriptions. Obtain executed agreements, full amendments, guarantor roster and collateral/intercreditor documents. Reported compliance is management language only; legal headroom and capacity remain Not calculable. |
| Earnings-adjustment substantiation | Adjustments 360/247; adjusted EBITDA 4,173/3,395 in FY2024/FY2023; earnings-quality, fundamental and model consumers | Annual pages 70-72 provide categories, not item-level recurrence, cash splits or lender eligibility. Obtain supporting schedules and acquisition/integration evidence. Use adjusted ratios only as disclosed sensitivities; no blanket acceptance of addbacks. |
| Incomplete quarterly normalization and historical liquidity | March/June periods; FY2023 undrawn facilities; earnings bridge, liquidity and forward-model consumers | Interim sources can support targeted work but only classification was retained here; no standalone opening-quarter source or discrete closing-quarter calculation delivered. Obtain/normalize only if those periods are required. Annual summary is not blocked by unrelated quarterly metrics. FY2023 liquidity total remains Not calculable. |
| Interest, FCF and lease definition limits | Net cash interest 1,158/1,160; FCF 1,880/1,236; gross debt 25,068/19,913; coverage, cash-flow and downside consumers | Annual pages 123, 145, 172. Gross cash interest, maintenance/growth capex and complete debt-like operating-lease treatment are not supplied in the selected base. Do not relabel net interest as gross, FCF as post-acquisition cash, or undiscounted lease payments as principal. |
| Residual non-debt liabilities and provisional accounting | Other current liabilities 186/169; other non-current liabilities 468/412; FY2024 acquisition accounting; fundamental, stress and recovery consumers | Annual pages 120, 144 leave residual composition/timing unextracted; page:144 says acquisition values remain subject to adjustment. Obtain material liability decomposition and final purchase allocations where needed. Unknown items are not assumed irrelevant; exact cash settlement and final valuation remain restricted. |
| Unreviewed content and alternate version | Unread annual/interim notes, PDF-only content and visuals; evidence validation and any consumer seeking facts outside retained spans | Reads were bounded, not a complete filing review. No visual checks or whole-document version reconciliation claimed. Retrieve only the missing passages needed for the requested conclusion; preserve source version and locator. |
| External decision evidence | Peer, market, ratings, forward operating assumptions; benchmarking, market, ratings and complete committee-action consumers | No external sources were supplied or used. Obtain dated peer/agency/price/curve evidence and clearly labeled scenario assumptions. This financial foundation alone cannot satisfy those analytical uses. |

### Downstream readiness by requested use

| Consumer(s) | Requirement assessment | Readiness and action |
| --- | --- | --- |
| CP-1A | Consolidated identity, annual business/segment and financing baseline available; transaction scope and operative parties incomplete | Limited: use historical fact foundation, not an invented live deal or complete legal entity map. |
| CP-1B | Annual income, segment and earnings bridges available; discrete-quarter and full organic/acquisition profit normalization incomplete | Limited: annual reported-period bridge can proceed; obtain quarter and driver evidence if required. |
| CP-1C | Issuer normalized annual baseline available; peer evidence absent | Not ready for complete benchmarking; obtain defined comparable peer sources. |
| CP-1D | Both EBITDA bridges, CFO reconciliation, addback categories and FCF available | Limited: run adjustment challenge; require substantiation before accepting recurring cash earnings. |
| CP-DR | Named source, cutoff, legal, liquidity and external evidence gaps supplied | Sufficient for scoped gap planning, not factual resolution from absent documents. |
| CP-2 | Annual financials, leverage, coverage, cash-flow and segment foundation available | Limited: bounded fundamental synthesis; retain source/date, cash access and adjustment qualifications. |
| CP-2A | Historical base, maturity exclusions and leverage definitions available | Limited: use explicit analyst scenarios; exact covenant failure point and operating stress assumptions remain missing. |
| CP-2D | Closing cash, facilities, FCF, declared payment and maturity timing available | Limited: static bridge can proceed; obtain monthly timing, cash access and draw conditions for runway. |
| CP-2E | Floating-rate facility summary available; no full hedge/FX extraction delivered here | Limited foundation only: target hedge and operating currency evidence before sensitivity conclusions. |
| CP-2G | Annual normalized statements, FCF construction and debt baseline available | Limited: projections need explicit assumptions, timing and acquisition normalization; no issuer forecast is implied. |
| CP-2H | Accounting ratios available; agency definitions, ratings and triggers absent | Not ready for migration/divergence conclusions; obtain dated agency evidence. |
| CP-3 | Instrument balances and rates available; market pricing and operative ranking/call terms absent | Not ready for complete relative value/security selection. |
| CP-3C | Gross debt and fiscal maturity schedule available; operative terms and financing access absent | Limited for maturity inventory, not ready for complete liability-management/refinancing assessment. |
| CP-3D | No dated trading/flow/quote evidence | Not ready; accounting fair value is not a substitute for market technicals. |
| CP-4 | Reported covenant descriptions and facility observations available, but unresolved definitions | Not ready for legal capacity/compliance calculation; obtain operative package and reconcile numerator conflict. |
| CP-4C | Consolidated balance sheet available; entity claims, priority and valuation support absent | Not ready for recovery/fulcrum modeling. |
| CP-5 | Source-located reported tables, calculated bridges and explicit limitations supplied | Limited: audit retained evidence and arithmetic; preparation/visual completeness remains unverified. |
| CP-6 | Historical credit findings supported; legal, market, agency and scenario gaps persist | Limited for challenge discussion, not ready for a complete investment action bias. |

No absent input is dismissed as irrelevant merely because annual accounting can be extracted. Each restriction above follows the affected use: missing legal definitions block legal ratios, not the bounded reported income statement; missing historical facility availability blocks that liquidity total, not FY2023 reported cash. Confidence judgments are qualitative lineage assessments, not a numerical QA certification.

## Next module

Pass this annual financial foundation and all retained gaps to **CP-1B** and **CP-1D**, with **CP-1A** using the business/segment and financing baseline. The priority analytical challenge is distinguishing sustainable cash earnings from management adjustments and testing cash availability after the declared shareholder payment.

For **CP-2D**, retain the separate receivables maturity, facility precision, lease exclusions and accrued-versus-paid distinction. For **CP-4**, do not calculate covenant headroom from the illustrative leverage ratios: resolve the operative numerator, denominator and entity perimeter first. Route missing legal, cash-access, cutoff and external evidence through **CP-DR**. Downstream publication must preserve the retrospective-date qualification, reported/calculated distinction and all definition-specific limitations.