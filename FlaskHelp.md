
 <!-- -------------------------------------------------------------------->
python -m venv venv
pip install virtualenv
virtualenv venv

├── app/                      # Ana uygulama klasörü
│   ├── __init__.py           # Flask uygulamasını başlatır (application factory burada olur)
│   ├── routes.py             # Tüm route’lar burada tanımlanabilir (views.py olarak da adlandırılabilir)
│   ├── models.py             # Veritabanı modelleri
│   ├── forms.py              # Flask-WTF formları varsa burada
│   ├── templates/            # HTML şablonları (Jinja2)
│   │   └── base.html         # Ana template (diğerleri bunu extend eder)
│   └── static/               # Statik dosyalar (CSS, JS, img)
        └── images/
        └── assets
│            ├── css/
│            ├── js/
│       
│
 <!-- -------------------------------------------------------------------->

from flask import Flask,render_template

app = Flask(__name__) 

@app.route('/')  
def home():
    return ('<h1 style="color:purple" >Hello, World!</h1>' \
    '<p>selamün aleyküm world</p>'
    )
    
if __name__ == "__main__":
    app.run(debug=True)
 
 <!-- -------------------------------------------------------------------->

@app.route("/username/<name>/<int:number>") #/username/<path:name>/
def greet(name, number):
    return f"Hello {name}, you are {number} years old"

 <!-- -------------------------------------------------------------------->

@app.route("/")
def home():
    return render_template("index.html")

 <!-- -------------------------------------------------------------------->
 
<link rel="stylesheet" href="/static/css/styles.css">

<img class="bottom-cloud" src="/static/images/cloud.png" alt="cloud">
<img class="mountain" src="/static/images/mountain.png" alt="mountain-img">


 <!-- -------------------------------------------------------------------->

  document.body.contentEditable = true

<!-- -------------------------------------------------------------------->


# Jinja

<h1> {{  5 * 6  }} <h1>

# passing values to templates 

              import random
main.py    >  random_number = random.randint(1,10)
              return render_template("index.html", num = random_number)



index.html > <h2> {{  num  }} <h2>
 

             {% for blog_post in posts: %}
             {%  if blog_post["id"] == 2          %}
                <h1> {{ blog_post["title"]    }} </h1>
                <h1> {{ blog_post["subtitle"] }} </h1>
                <p>  {{ blog_post["body"] }}    </p>
                {% endif  %}
             {% endfor  %}



<a href="{{ url_for('get_blog',num=3)  }}">Go To Blog</a>





<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{% block title %}Dashboard{% endblock %}</title>
    <!-- CSS ve diğer head içerikleri -->
</head>
<body>

    {% include "header.html" %}
    {% include "leftsidebar.html" %}

    <div class="page-wrapper">
        {% block content %}{% endblock %}
    </div>

    {% include "footer.html" %}
    
</body>
</html>