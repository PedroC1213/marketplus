import os

folders = [
    "src/components/layout",
    "src/components/ui",
    "src/components/auth",
    "src/components/dashboard",
    "src/components/reviews",
    "src/components/campaigns",
    "src/components/sellers",
    "src/layouts",
    "src/pages/reviews",
    "src/styles",
    "src/utils"
]

files = [
    "src/components/layout/Navbar.astro",
    "src/components/layout/Sidebar.astro",
    "src/components/layout/Footer.astro",
    "src/components/ui/Button.astro",
    "src/components/ui/Card.astro",
    "src/components/ui/Badge.astro",
    "src/components/auth/LoginForm.jsx",
    "src/components/auth/RegisterForm.jsx",
    "src/components/dashboard/RiskChart.jsx",
    "src/components/dashboard/TrendChart.jsx",
    "src/components/dashboard/AlertsWidget.jsx",
    "src/components/reviews/ReviewsTable.jsx",
    "src/components/reviews/ReviewDetail.jsx",
    "src/components/campaigns/CampaignsList.jsx",
    "src/components/sellers/SellersTable.jsx",
    "src/layouts/Layout.astro",
    "src/pages/index.astro",
    "src/pages/login.astro",
    "src/pages/register.astro",
    "src/pages/dashboard.astro",
    "src/pages/campaigns.astro",
    "src/pages/sellers.astro",
    "src/pages/profile.astro",
    "src/pages/404.astro",
    "src/pages/reviews/index.astro",
    "src/pages/reviews/[id].astro",
    "src/styles/global.css",
    "src/utils/api.js"
]

for folder in folders:
    os.makedirs(folder, exist_ok=True)

for file in files:
    open(file, 'a').close()  # crea vacío
    print(f"✅ {file}")

print("Estructura completa generada.")