Flixora AI Sales Agent ko Render.com par host karna bahut aasan hai kyunki aapke project me already render.yaml, Procfile, aur requirements.txt configured hain.

Yahan Step-by-Step Guide hai:

Step 1: Apne Code ko GitHub par Push karein
Render aapke GitHub repository se connect hoke deploy karta hai. Sabse pehle local changes GitHub par push karein:

Terminal / PowerShell me ye run karein:

bash
git add .
git commit -m "feat: complete sales agent with dark mode, prd editor and live llm fixes"
git push origin main
Step 2: Render par Account banayein & Login karein
Browser me render.com par jayein.
"Sign In" par click karke "GitHub" se sign in karein (taaki aapke repos direct access ho sakein).
Step 3: Naya Web Service Create karein
Render Dashboard par "New +" button par click karein aur "Web Service" choose karein.
"Build and deploy from a Git repository" select karke Next karein.
Apni repository (Ai-Sale-Automation-) ko select karein aur "Connect" par click karein.
Step 4: Web Service Settings Fill karein
Aapke samne setup form aayega, usme ye details enter karein:

Field	Kya Daalna Hai
Name	flixora-ai-sales (ya aapki marzi ka koi bhi naam)
Region	Singapore ya Frankfurt (India ke liye best speed)
Branch	main
Root Directory	(Khaali chhod dein)
Runtime	Python 3
Build Command	pip install -r requirements.txt
Start Command	flask init-db && gunicorn app:app --bind 0.0.0.0:$PORT --workers 2
Instance Type	Free ($0/month)
Step 5: Environment Variables Add karein (Sabse Zaroori Step ⚠️)
Usi page par neeche "Environment Variables" section milega. "Add Environment Variable" par click karke ye key-values add karein:

FLASK_ENV
Value: production
SECRET_KEY
Value: fOKwU0gEujOsWrU6vnuX5IKH9furE8hkzaZVB9CTZD4= (ya koi bhi random secure string)
ENCRYPTION_KEY (Very Important - Credentials decrypt karne ke liye)
Value: RJby_GfHBHwOdxMt2X8qGxrgK_6Xpx7LDqm3dX64EJM=
ADMIN_USERNAME
Value: admin
ADMIN_PASSWORD
Value: admin123 (ya jo password aap dashboard login ke liye chahte hain)
ADMIN_EMAIL
Value: admin@flixora.com
TEST_MODE
Value: false
OPENROUTER_API_KEY
Value: Aapki fresh OpenRouter API key (sk-or-v1-...)
Step 6: Deploy karein!
Page ke bottom me "Deploy Web Service" button par click karein.
Render build start karega:
Saare packages install honge (pip install -r requirements.txt).
flask init-db command run hoke saare database tables, admin account, aur default knowledge items auto-create karega.
gunicorn server start ho jayega.
2-3 minute me terminal log me Your service is live 🎉 likha hua aayega!
Step 7: App Open karein aur Login karein
Render dashboard ke top par aapko live link mil jayegi (jaise: https://flixora-ai-sales.onrender.com).
Us link ko open karein aur login karein:
Username: admin
Password: admin123 (ya jo password aapne environment variable me daala)
TIP

Free Tier Sleep Note: Render ka Free Web Service 15 minute inactivity ke baad sleep mode me chala jata hai. Jab bhi aap ya koi client link open karega, first request 30-40 seconds take karegi wake up hone me, uske baad instant fast chalegi.
