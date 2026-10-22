// =====================================================================
// power_query.m  |  Power Query (M) scripts for each table
// Usage: Power BI Desktop > Get Data > Blank Query > Advanced Editor,
//        paste one block per query and rename the query as shown.
// Set the FolderPath parameter to the local path of the /data folder.
// =====================================================================

// ---------- Parameter: FolderPath  (Manage Parameters > New, Type = Text)
"C:\Projects\sales-analysis\data\" meta [IsParameterQuery = true, Type = "Text", IsParameterQueryRequired = true]


// ---------- Query: fact_sales
let
    Source      = Csv.Document(File.Contents(FolderPath & "fact_sales.csv"),
                    [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted    = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed       = Table.TransformColumnTypes(Promoted, {
                    {"order_id", type text}, {"order_date", type date}, {"ship_date", type date},
                    {"customer_id", type text}, {"product_id", Int64.Type}, {"rep_id", Int64.Type},
                    {"region_id", Int64.Type}, {"channel", type text}, {"payment_mode", type text},
                    {"quantity", Int64.Type}, {"unit_price", Currency.Type},
                    {"discount_pct", type number}, {"sales_amount", Currency.Type},
                    {"cost_amount", Currency.Type}, {"profit", Currency.Type},
                    {"is_returned", type logical}}, "en-US"),
    // Data cleaning: remove duplicate orders, fill blank channel
    Deduped     = Table.Distinct(Typed, {"order_id"}),
    FillChannel = Table.ReplaceValue(Deduped, null, "Unknown", Replacer.ReplaceValue, {"channel"}),
    AddShipDays = Table.AddColumn(FillChannel, "ship_days",
                    each Duration.Days([ship_date] - [order_date]), Int64.Type),
    AddDiscBand = Table.AddColumn(AddShipDays, "discount_band", each
                    if [discount_pct] = 0 then "No discount"
                    else if [discount_pct] <= 0.10 then "1-10%"
                    else if [discount_pct] <= 0.20 then "11-20%"
                    else ">20%", type text)
in
    AddDiscBand


// ---------- Query: dim_products
let
    Source   = Csv.Document(File.Contents(FolderPath & "dim_products.csv"), [Delimiter = ",", Encoding = 65001]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed    = Table.TransformColumnTypes(Promoted, {
                 {"product_id", Int64.Type}, {"product_name", type text}, {"category", type text},
                 {"sub_category", type text}, {"unit_price", Currency.Type}, {"unit_cost", Currency.Type}}, "en-US")
in
    Typed


// ---------- Query: dim_customers
let
    Source   = Csv.Document(File.Contents(FolderPath & "dim_customers.csv"), [Delimiter = ",", Encoding = 65001]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed    = Table.TransformColumnTypes(Promoted, {
                 {"customer_id", type text}, {"customer_name", type text}, {"segment", type text},
                 {"region_id", Int64.Type}, {"city", type text}, {"signup_date", type date}}, "en-US")
in
    Typed


// ---------- Query: dim_regions
let
    Source   = Csv.Document(File.Contents(FolderPath & "dim_regions.csv"), [Delimiter = ",", Encoding = 65001]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed    = Table.TransformColumnTypes(Promoted, {
                 {"region_id", Int64.Type}, {"region_name", type text}, {"country", type text}})
in
    Typed


// ---------- Query: dim_sales_reps
let
    Source   = Csv.Document(File.Contents(FolderPath & "dim_sales_reps.csv"), [Delimiter = ",", Encoding = 65001]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed    = Table.TransformColumnTypes(Promoted, {
                 {"rep_id", Int64.Type}, {"rep_name", type text}, {"region_id", Int64.Type},
                 {"hire_date", type date}, {"annual_target", Currency.Type}}, "en-US")
in
    Typed
