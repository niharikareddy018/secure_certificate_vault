import os
import hashlib
from datetime import timedelta, datetime
from werkzeug.utils import secure_filename
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity, get_jwt
Web3 = None
from solcx import install_solc, compile_source
import bcrypt

from backend.config import Config
from backend.models import db, User, Certificate

ALLOWED_EXTENSIONS = {"pdf"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def create_app():
    root_dir = os.path.dirname(__file__)
    static_dir = os.path.abspath(os.path.join(root_dir, "..", "frontend"))
    app = Flask(__name__, static_folder=static_dir, static_url_path="/")
    app.config.from_object(Config)
    CORS(app, supports_credentials=True)

    db.init_app(app)
    with app.app_context():
        try:
            db.create_all()
        except Exception:
            pass
    jwt = JWTManager(app)

    try:
        from web3 import Web3 as _Web3
        globals()["Web3"] = _Web3
    except Exception as e:
        app.logger.warning(f"Web3 import unavailable: {e}")

    # Web3 setup - make it non-blocking if provider unavailable
    provider = Config.build_web3_provider()
    w3 = None
    try:
        if Web3 is not None:
            w3 = Web3(Web3.HTTPProvider(provider))
    except Exception as e:
        app.logger.warning(f"Web3 provider unavailable: {e}")
    
    contract_address = app.config.get("CONTRACT_ADDRESS")
    contract = None

    source = None
    contract_path = os.path.join(root_dir, "CertificateVerification.sol")
    with open(contract_path, "r", encoding="utf-8") as f:
        source = f.read()

    def ensure_contract():
        nonlocal contract_address, contract, w3
        if contract is not None:
            return contract
        if w3 is None or not w3.is_connected():
            return None
        if contract_address:
            compiled = compile_source(source, output_values=["abi"])
            interface = list(compiled.values())[0]
            abi = interface["abi"]
            contract = w3.eth.contract(address=Web3.to_checksum_address(contract_address), abi=abi)
            return contract
        if os.getenv("VERCEL"):
            return None
        install_solc("0.8.20")
        compiled = compile_source(source, output_values=["abi", "bin"], solc_version="0.8.20")
        interface = list(compiled.values())[0]
        abi = interface["abi"]
        bytecode = interface["bin"]
        if len(w3.eth.accounts) == 0:
            return None
        w3.eth.default_account = w3.eth.accounts[0]
        Contract = w3.eth.contract(abi=abi, bytecode=bytecode)
        tx_hash = Contract.constructor().transact({"from": w3.eth.default_account})
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        contract_address = tx_receipt.contractAddress
        app.config["CONTRACT_ADDRESS"] = contract_address
        contract = w3.eth.contract(address=contract_address, abi=abi)
        return contract

    @app.route("/api/register", methods=["POST"])
    def register():
        data = request.get_json()
        if not data:
            return jsonify({"error": "invalid body"}), 400
        email = (data.get("email") or "").strip().lower()
        password = data.get("password") or ""
        role = (data.get("role") or "").strip().lower()
        if role not in {"issuer", "student"}:
            return jsonify({"error": "invalid role"}), 400
        if not email or not password:
            return jsonify({"error": "missing fields"}), 400
        if User.query.filter_by(email=email).first():
            return jsonify({"error": "email exists"}), 400
        salt = bcrypt.gensalt()
        pw_hash = bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")
        u = User(email=email, password_hash=pw_hash, role=role)
        db.session.add(u)
        db.session.commit()
        return jsonify({"message": "registered"})

    @app.route("/api/login", methods=["POST"])
    def login():
        data = request.get_json()
        if not data:
            return jsonify({"error": "invalid body"}), 400
        email = (data.get("email") or "").strip().lower()
        password = data.get("password") or ""
        u = User.query.filter_by(email=email).first()
        if not u:
            return jsonify({"error": "invalid credentials"}), 401
        valid = bcrypt.checkpw(password.encode("utf-8"), u.password_hash.encode("utf-8"))
        if not valid:
            return jsonify({"error": "invalid credentials"}), 401
        token = create_access_token(identity=str(u.id), additional_claims={"role": u.role, "email": u.email}, expires_delta=timedelta(hours=12))
        return jsonify({"access_token": token})

    @app.route("/api/me", methods=["GET"])
    @jwt_required()
    def me():
        uid = get_jwt_identity()
        claims = get_jwt()
        return jsonify({"id": int(uid), "role": claims.get("role"), "email": claims.get("email")})

    @app.route("/api/certificates", methods=["POST"])
    @jwt_required()
    def issue():
        uid = get_jwt_identity()
        claims = get_jwt()
        role = claims.get("role")
        if role not in {"issuer", "student"}:
            return jsonify({"error": "forbidden"}), 403
        student_name = (request.form.get("student_name") or "").strip()
        student_email = (request.form.get("student_email") or "").strip().lower()
        if role == "student":
            student_email = (claims.get("email") or "").strip().lower()
        course_name = (request.form.get("course_name") or "").strip()
        issue_date_str = (request.form.get("issue_date") or "").strip()
        f = request.files.get("file")
        if not f or f.filename == "":
            return jsonify({"error": "file required"}), 400
        if not allowed_file(f.filename):
            return jsonify({"error": "only pdf"}), 400
        try:
            issue_date = datetime.strptime(issue_date_str, "%Y-%m-%d").date()
        except Exception:
            try:
                issue_date = datetime.strptime(issue_date_str, "%d-%m-%Y").date()
            except Exception:
                return jsonify({"error": "invalid date"}), 400
        filename = secure_filename(f.filename)
        os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
        path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        base, ext = os.path.splitext(filename)
        i = 1
        while os.path.exists(path):
            filename = f"{base}_{i}{ext}"
            path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            i += 1
        f.save(path)
        digest = sha256_file(path)
        c = ensure_contract()
        tx_hash_hex = None
        addr = None
        if c is not None:
            if len(w3.eth.accounts) > 0 and w3.eth.default_account is None:
                w3.eth.default_account = w3.eth.accounts[0]
            hash_bytes32 = Web3.to_bytes(hexstr=digest)
            tx = c.functions.store(hash_bytes32).transact({"from": w3.eth.default_account})
            receipt = w3.eth.wait_for_transaction_receipt(tx)
            tx_hash_hex = receipt.transactionHash.hex()
            addr = c.address
        cert = Certificate(
            student_name=student_name,
            student_email=student_email,
            course_name=course_name,
            issue_date=issue_date,
            file_path=path,
            file_hash="0x" + digest,
            blockchain_tx=tx_hash_hex,
            contract_address=addr,
            issuer_id=int(uid),
        )
        db.session.add(cert)
        cid = None
        try:
            db.session.commit()
            cid = cert.id
        except Exception:
            db.session.rollback()
        return jsonify({
            "id": cid,
            "hash": cert.file_hash,
            "tx": tx_hash_hex,
            "contract": addr,
            "filename": filename,
            "download_url": f"/uploads/{filename}",
        })

    @app.route("/api/certificates", methods=["GET"])
    @jwt_required()
    def list_my():
        uid = get_jwt_identity()
        claims = get_jwt()
        if claims.get("role") == "issuer":
            rows = Certificate.query.filter_by(issuer_id=int(uid)).order_by(Certificate.created_at.desc()).all()
        else:
            rows = Certificate.query.filter_by(student_email=claims.get("email")).order_by(Certificate.created_at.desc()).all()
        result = []
        for r in rows:
            filename = os.path.basename(r.file_path) if r.file_path else None
            result.append({
                "id": r.id,
                "student_name": r.student_name,
                "student_email": r.student_email,
                "course_name": r.course_name,
                "issue_date": r.issue_date.isoformat(),
                "file_hash": r.file_hash,
                "blockchain_tx": r.blockchain_tx,
                "contract_address": r.contract_address,
                "filename": filename,
                "download_url": f"/uploads/{filename}" if filename else None,
            })
        return jsonify(result)

    @app.route("/api/verify", methods=["GET"])
    def verify():
        h = (request.args.get("hash") or "").strip()
        if not h:
            return jsonify({"error": "hash required"}), 400
        c = ensure_contract()
        on_chain = False
        issuer = None
        ts = None
        if c is not None:
            try:
                exists = c.functions.exists(Web3.to_bytes(hexstr=h)).call()
                on_chain = bool(exists)
                if on_chain:
                    res = c.functions.get(Web3.to_bytes(hexstr=h)).call()
                    issuer = res[0]
                    ts = int(res[1])
            except Exception:
                on_chain = False
        in_db = Certificate.query.filter_by(file_hash=h).first()
        meta = None
        if in_db:
            meta = {
                "student_name": in_db.student_name,
                "student_email": in_db.student_email,
                "course_name": in_db.course_name,
                "issue_date": in_db.issue_date.isoformat(),
                "issuer_id": in_db.issuer_id,
            }
        return jsonify({"on_chain": on_chain, "issuer": issuer, "timestamp": ts, "meta": meta})

    @app.route("/api/stats", methods=["GET"])
    @jwt_required()
    def stats():
        claims = get_jwt()
        if claims.get("role") != "issuer":
            return jsonify({"error": "forbidden"}), 403
        users = User.query.count()
        certs = Certificate.query.count()
        return jsonify({"users": users, "certificates": certs})

    @app.route("/uploads/<path:filename>", methods=["GET"])
    @jwt_required()
    def download(filename):
        uid = get_jwt_identity()
        claims = get_jwt()
        cert = Certificate.query.filter_by(file_path=os.path.join(app.config["UPLOAD_FOLDER"], filename)).first()
        if cert is None:
            return jsonify({"error": "not found"}), 404
        if claims.get("role") == "issuer" and cert.issuer_id == int(uid):
            pass
        elif claims.get("role") == "student" and cert.student_email == claims.get("email"):
            pass
        else:
            return jsonify({"error": "forbidden"}), 403
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename, as_attachment=True)

    @app.route("/health")
    def health():
        """Health check endpoint for Railway/Render"""
        return jsonify({"status": "ok", "service": "certificate-api"}), 200

    @app.route("/")
    def index():
        # If frontend isn't deployed with the API, this may 404 on static file; return health
        index_path = os.path.join(static_dir, "index.html")
        if os.path.exists(index_path):
            return app.send_static_file("index.html")
        return jsonify({"status": "ok", "service": "certificate-api"}), 200

    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
