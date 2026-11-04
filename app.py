import os
import urllib.parse
from functools import wraps
from flask import Flask, render_template, redirect, url_for, request, flash, make_response, abort
from flask_login import LoginManager, login_required, current_user, login_user, logout_user

from models import db, Permission, Role, User, Follow, Category, Brand, Device, Post, PostComment, ReviewComment
from markdown_utils import render_markdown, COMMENT_ALLOWED_TAGS

base_dir = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, template_folder=os.path.join(base_dir, "templates"))
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "student-techgadget-secret-key-2026")

db_file = os.path.join(base_dir, "techgadget.db")
if os.environ.get("DATABASE_URI"):
    db_uri = os.environ.get("DATABASE_URI")
    if db_uri.startswith("postgres://"):
        db_uri = db_uri.replace("postgres://", "postgresql://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = db_uri
elif os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
    import shutil
    import tempfile
    tmp_db = os.path.join(tempfile.gettempdir(), "techgadget.db")
    if os.path.exists(db_file) and not os.path.exists(tmp_db):
        shutil.copyfile(db_file, tmp_db)
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{tmp_db.replace(os.sep, '/')}"
elif os.name == "nt":
    try:
        import pyodbc
        odbc_str = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost\\SQLEXPRESS;DATABASE=TechGadget_CMS;Trusted_Connection=yes;TrustServerCertificate=yes;"
        app.config["SQLALCHEMY_DATABASE_URI"] = f"mssql+pyodbc:///?odbc_connect={urllib.parse.quote_plus(odbc_str)}"
    except Exception:
        app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_file}"
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_file}"

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def permission_required(permission):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.can(permission):
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def admin_required(f):
    return permission_required(Permission.ADMIN)(f)

def init_db():
    with app.app_context():
        db.create_all()
        if User.query.first() is None:
            Role.insert_roles()
            admin_role = Role.query.filter_by(name="Admin").first()
            reviewer_role = Role.query.filter_by(name="Reviewer").first()
            member_role = Role.query.filter_by(name="Member").first()

            c1 = Category(name="Smartphone")
            c2 = Category(name="Laptop")
            c3 = Category(name="Âm thanh")
            c4 = Category(name="Phụ kiện")
            db.session.add_all([c1, c2, c3, c4])

            b1 = Brand(name="Apple")
            b2 = Brand(name="Samsung")
            b3 = Brand(name="Sony")
            b4 = Brand(name="Asus")
            db.session.add_all([b1, b2, b3, b4])
            db.session.flush()

            u1 = User(email="tam@techgadget.vn", username="tam_admin", role=admin_role)
            u1.set_password("pass123")
            u2 = User(email="an@techgadget.vn", username="an_reviewer", role=reviewer_role)
            u2.set_password("pass123")
            u3 = User(email="binh@techgadget.vn", username="binh_tech", role=member_role)
            u3.set_password("pass123")
            db.session.add_all([u1, u2, u3])
            db.session.flush()

            db.session.add_all([
                Follow(follower_id=u3.id, followed_id=u2.id),
                Follow(follower_id=u3.id, followed_id=u1.id),
                Follow(follower_id=u2.id, followed_id=u1.id)
            ])

            d1 = Device(
                name="iPhone 15 Pro Max",
                price=29990000,
                specs="Chip A17 Pro, Màn hình 6.7 inch OLED 120Hz, Camera 48MP, Khung viền Titan.",
                image_url="https://images.unsplash.com/photo-1695048133142-1a20484d2569?auto=format&fit=crop&w=600&q=80",
                category=c1,
                brand=b1
            )
            d2 = Device(
                name="MacBook Pro M3",
                price=39990000,
                specs="Apple M3 Chip, 16GB RAM, 512GB SSD, Màn hình Liquid Retina XDR 14 inch.",
                image_url="https://images.unsplash.com/photo-1517336714731-489689fd1ca8?auto=format&fit=crop&w=600&q=80",
                category=c2,
                brand=b1
            )
            d3 = Device(
                name="Sony WH-1000XM5",
                price=7490000,
                specs="Tai nghe chống ồn chủ động ANC đỉnh cao, thời lượng pin 30 giờ, kết nối đa điểm.",
                image_url="https://images.unsplash.com/photo-1546435770-a3e426bf472b?auto=format&fit=crop&w=600&q=80",
                category=c3,
                brand=b3
            )
            d4 = Device(
                name="Asus ROG Zephyrus G16",
                price=45000000,
                specs="Intel Core Ultra 9, RTX 4070, Màn hình OLED 2.5K 240Hz, thiết kế kim loại mỏng nhẹ.",
                image_url="https://images.unsplash.com/photo-1603302576837-37561b2e2302?auto=format&fit=crop&w=600&q=80",
                category=c2,
                brand=b4
            )
            db.session.add_all([d1, d2, d3, d4])
            db.session.flush()

            post1_md = "## Tổng quan\nSau hơn nửa năm sử dụng làm máy chính, **MacBook Pro M3** thực sự đem lại hiệu năng ấn tượng cùng thời lượng pin bền bỉ.\n\n### Điểm mạnh\n- Thời lượng pin lên đến **18 tiếng** liên tục.\n- Màn hình Liquid Retina XDR hiển thị màu sắc cực kỳ chuẩn xác.\n- Quạt tản nhiệt hầu như không bao giờ phải hoạt động khi làm việc văn phòng và lập trình cơ bản.\n\n### Kết luận\nĐây là chiếc laptop hoàn hảo cho lập trình viên và những ai làm việc sáng tạo nội dung cần một thiết bị ổn định."
            post2_md = "## 5 phụ kiện công nghệ đáng sở hữu\nDanh sách các phụ kiện tăng năng suất làm việc cho anh em lập trình viên và sáng tạo nội dung:\n\n1. **Củ sạc GaN 100W**: Nhỏ gọn, sạc cùng lúc cả laptop, điện thoại và tai nghe.\n2. **Bàn phím cơ không dây switch êm**: Giúp gõ văn bản cả ngày không mỏi tay.\n3. **Chuột công thái học**: Bảo vệ khớp cổ tay khi làm việc lâu dài.\n4. **Tai nghe chống ồn chủ động**: Giữ không gian tập trung tối đa ở quán cà phê.\n5. **Hub chuyển đổi đa năng**: Mở rộng cổng kết nối HDMI, Type-C và thẻ nhớ."
            post3_md = "## Bí quyết giữ pin điện thoại bền lâu\nPin lithium-ion sẽ bền hơn nếu bạn lưu ý các nguyên tắc đơn giản sau:\n\n- Giới hạn mức sạc ở mức **80%** nếu điện thoại có hỗ trợ tính năng bảo vệ pin.\n- Tránh vừa sạc nhanh vừa chơi game nặng khiến máy bị quá nhiệt.\n- Không để pin cạn kiệt về **0%** thường xuyên.\n- Sử dụng củ sạc và cáp sạc chính hãng có chứng chỉ an toàn."

            p1 = Post(
                title="Đánh giá chi tiết MacBook Pro M3 sau 6 tháng sử dụng",
                image_url="https://images.unsplash.com/photo-1517336714731-489689fd1ca8?auto=format&fit=crop&w=800&q=80",
                body_md=post1_md,
                body_html=render_markdown(post1_md),
                author=u1
            )
            p2 = Post(
                title="Top 5 phụ kiện công nghệ đáng mua nhất 2026",
                image_url="https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=800&q=80",
                body_md=post2_md,
                body_html=render_markdown(post2_md),
                author=u2
            )
            p3 = Post(
                title="Mẹo tối ưu thời lượng pin cho điện thoại thông minh",
                image_url="https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?auto=format&fit=crop&w=800&q=80",
                body_md=post3_md,
                body_html=render_markdown(post3_md),
                author=u1
            )
            db.session.add_all([p1, p2, p3])
            db.session.flush()

            c_post1 = PostComment(
                post_id=p1.id,
                author_id=u3.id,
                body_md="Bài viết đánh giá rất khách quan và thực tế! Mình cũng đang dùng bản M3 16GB RAM thấy rất mượt mà.",
                body_html=render_markdown("Bài viết đánh giá rất khách quan và thực tế! Mình cũng đang dùng bản M3 16GB RAM thấy rất mượt mà.", COMMENT_ALLOWED_TAGS)
            )
            c_post2 = PostComment(
                post_id=p2.id,
                author_id=u1.id,
                body_md="Chuột công thái học là món đồ **rất đáng đầu tư**, dùng quen rồi không muốn quay lại chuột thường luôn.",
                body_html=render_markdown("Chuột công thái học là món đồ **rất đáng đầu tư**, dùng quen rồi không muốn quay lại chuột thường luôn.", COMMENT_ALLOWED_TAGS)
            )
            db.session.add_all([c_post1, c_post2])

            rev1_md = "Camera chụp đêm cực kỳ ấn tượng, khung viền titan nhẹ hơn hẳn đời trước. **Rất đáng tiền!**"
            rev2_md = "Pin trâu, bàn phím gõ nảy, loa nghe nhạc hay nhất trong các dòng laptop hiện nay."
            r1 = ReviewComment(device_id=d1.id, author_id=u3.id, body_md=rev1_md, body_html=render_markdown(rev1_md, COMMENT_ALLOWED_TAGS))
            r2 = ReviewComment(device_id=d2.id, author_id=u2.id, body_md=rev2_md, body_html=render_markdown(rev2_md, COMMENT_ALLOWED_TAGS))
            db.session.add_all([r1, r2])

            db.session.commit()

@app.route("/")
@app.route("/api/index")
@app.route("/api/index.py")
def home():
    show_param = request.args.get("show")
    if show_param in ("followed", "all"):
        show_followed = (show_param == "followed")
    else:
        show_followed = request.cookies.get("show_followed", "0") == "1"

    if current_user.is_authenticated and show_followed:
        posts = current_user.followed_posts.all()
    else:
        posts = Post.query.order_by(Post.created_at.desc()).all()

    resp = make_response(render_template("home.html", posts=posts, show_followed=show_followed))
    if show_param in ("followed", "all"):
        resp.set_cookie("show_followed", "1" if show_followed else "0", max_age=30 * 24 * 3600)
    return resp

@app.route("/quick-login/<username>")
def quick_login(username):
    user = User.query.filter_by(username=username).first_or_404()
    login_user(user)
    flash(f"Đã đăng nhập nhanh với tài khoản {username}.")
    return redirect(url_for("home"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("home"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash("Đăng nhập thành công.")
            return redirect(url_for("home"))
        flash("Tên đăng nhập hoặc mật khẩu không đúng.")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Đã đăng xuất.")
    return redirect(url_for("home"))

@app.route("/users/<username>")
def profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    is_following = current_user.is_authenticated and current_user.is_following(user)
    followers_count = Follow.query.filter_by(followed_id=user.id).count()
    following_count = Follow.query.filter_by(follower_id=user.id).count()
    user_posts = Post.query.filter_by(author_id=user.id).order_by(Post.created_at.desc()).all()
    return render_template("profile.html", user=user, is_following=is_following,
                           followers_count=followers_count, following_count=following_count,
                           posts=user_posts)

@app.route("/users/<username>/follow", methods=["POST"])
@login_required
def toggle_follow(username):
    user = User.query.filter_by(username=username).first_or_404()
    if user.id == current_user.id:
        flash("Bạn không thể tự theo dõi chính mình.")
        return redirect(url_for("profile", username=username))
    if current_user.is_following(user):
        current_user.unfollow(user)
        flash(f"Đã hủy theo dõi {username}.")
    else:
        current_user.follow(user)
        flash(f"Đã theo dõi {username}.")
    db.session.commit()
    return redirect(url_for("profile", username=username))

@app.route("/posts")
def post_list():
    page = request.args.get("page", 1, type=int)
    posts = Post.query.order_by(Post.created_at.desc()).paginate(page=page, per_page=3, error_out=False)
    return render_template("post_list.html", posts=posts)

@app.route("/posts/<int:post_id>", methods=["GET", "POST"])
def post_detail(post_id):
    post = Post.query.get_or_404(post_id)
    if request.method == "POST":
        if not current_user.is_authenticated:
            flash("Vui lòng đăng nhập để gửi bình luận.")
            return redirect(url_for("login"))
        body_md = request.form.get("body_md", "").strip()
        if not body_md:
            flash("Nội dung bình luận không được để trống.")
            return redirect(url_for("post_detail", post_id=post.id))
        body_html = render_markdown(body_md, allowed_tags=COMMENT_ALLOWED_TAGS)
        comment = PostComment(post_id=post.id, author_id=current_user.id, body_md=body_md, body_html=body_html)
        db.session.add(comment)
        db.session.commit()
        flash("Đã gửi bình luận thành công.")
        return redirect(url_for("post_detail", post_id=post.id))
    return render_template("post_detail.html", post=post)

@app.route("/posts/new", methods=["GET", "POST"])
@login_required
def post_new():
    if not current_user.can(Permission.CREATE_POST):
        flash("Bạn không có quyền đăng bài viết.")
        return redirect(url_for("post_list"))
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        image_url = request.form.get("image_url", "").strip()
        body_md = request.form.get("body_md", "").strip()
        if not title or not body_md:
            flash("Vui lòng nhập đầy đủ tiêu đề và nội dung bài viết.")
            return render_template("post_form.html", title=title, image_url=image_url, body_md=body_md)
        body_html = render_markdown(body_md)
        post = Post(title=title, image_url=image_url or None, body_md=body_md, body_html=body_html, author_id=current_user.id)
        db.session.add(post)
        db.session.commit()
        flash("Đã đăng bài viết mới thành công.")
        return redirect(url_for("post_detail", post_id=post.id))
    return render_template("post_form.html")

@app.route("/devices")
def device_list():
    devices = Device.query.filter_by(is_deleted=False).all()
    return render_template("device_list.html", devices=devices)

@app.route("/devices/<int:device_id>")
def device_detail(device_id):
    device = Device.query.get_or_404(device_id)
    return render_template("device_detail.html", device=device)

@app.route("/devices/new", methods=["GET", "POST"])
@login_required
def device_new():
    if not current_user.can(Permission.CREATE_POST):
        flash("Bạn không có quyền thêm thiết bị mới.")
        return redirect(url_for("device_list"))
    categories = Category.query.all()
    brands = Brand.query.all()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        price = request.form.get("price", 0, type=int)
        specs = request.form.get("specs", "").strip()
        image_url = request.form.get("image_url", "").strip()
        category_id = request.form.get("category_id", type=int)
        brand_id = request.form.get("brand_id", type=int)
        if not name or not category_id or not brand_id:
            flash("Vui lòng điền đủ tên, danh mục và hãng.")
            return render_template("device_form.html", categories=categories, brands=brands)
        device = Device(name=name, price=price, specs=specs, image_url=image_url or None, category_id=category_id, brand_id=brand_id)
        db.session.add(device)
        db.session.commit()
        flash("Đã thêm thiết bị mới thành công.")
        return redirect(url_for("device_list"))
    return render_template("device_form.html", categories=categories, brands=brands)

@app.route("/devices/<int:device_id>/reviews", methods=["GET", "POST"])
def device_reviews(device_id):
    device = Device.query.get_or_404(device_id)
    if request.method == "POST":
        if not current_user.is_authenticated:
            flash("Vui lòng đăng nhập để gửi đánh giá.")
            return redirect(url_for("login"))
        body_md = request.form.get("body_md", "").strip()
        if not body_md:
            flash("Nội dung đánh giá không được để trống.")
            return redirect(url_for("device_reviews", device_id=device.id))
        body_html = render_markdown(body_md, allowed_tags=COMMENT_ALLOWED_TAGS)
        review = ReviewComment(device_id=device.id, author_id=current_user.id, body_md=body_md, body_html=body_html)
        db.session.add(review)
        db.session.commit()
        flash("Đã gửi đánh giá thành công.")
        return redirect(url_for("device_reviews", device_id=device.id))
    reviews = ReviewComment.query.filter_by(device_id=device.id).order_by(ReviewComment.created_at.desc()).all()
    return render_template("device_reviews.html", device=device, reviews=reviews)

with app.app_context():
    try:
        init_db()
    except Exception:
        pass

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
