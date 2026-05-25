# VHS Tape Script for QuerySage Demo
Output demo.gif

Set FontSize 14
Set FontFamily "JetBrains Mono"
Set Width 1200
Set Height 600
Set Padding 20
Set Theme "Dracula"
Set WindowBar "Colorful"

# Spin up Postgres + Pagila DB container
Type "docker compose up -d"
Sleep 1s
Enter
Sleep 3s

# Analyze the poorly written query using the QuerySage CLI
Type "querysage analyze --file backend/tests/fixtures/demo_queries/terrible_query.sql --db 1"
Sleep 1.5s
Enter
Sleep 6s

# Exit
Type "exit"
Sleep 1s
Enter
