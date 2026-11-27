KUL071 Site Tracker - standalone (Netlify)
1. Upload all these files to a new GitHub repository.
2. In Netlify: Add new project > Import from Git > pick the repository > Deploy.
3. Netlify > Project configuration > Environment variables:
   TEAM_PIN  = PIN for site team (e.g. 4821)
   ADMIN_PIN = PIN for the planner (e.g. 9087)
   Then Deploys > Trigger deploy.
4. Open the site link, enter name + PIN. Planner uses ADMIN_PIN (can load XER, reset, export).
AI assistant uses Netlify AI Gateway automatically after the first production deploy.
