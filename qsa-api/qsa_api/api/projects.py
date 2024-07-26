# coding: utf8
import sys
import shutil
import requests
from jsonschema import validate
from jsonschema.exceptions import ValidationError
from flask import send_file, Blueprint, jsonify, request

from qgis.PyQt.QtCore import QDateTime

from ..wms import WMS
from ..project import QSAProject
from ..project import logger

import json


projects = Blueprint("projects", __name__)


@projects.get("/")
def projects_list():
    try:
        logger().info("")
        psql_schema = request.args.get("schema", default="public")

        p = []
        for project in QSAProject.projects(psql_schema):
            p.append(project.name)
        logger().info(jsonify(p))
        return jsonify(p)

    except Exception as e:
        logger().exception(str(e))
        return {"error": "Could not get project list"}, 415


@projects.get("/<name>")
def project_info(name: str):
    try:
        logger().info(name)
        psql_schema = request.args.get("schema", default="public")
        project = QSAProject(name, psql_schema)

        if not project.exists():
            raise Exception("Project does not exist")
        logger().info(jsonify(project.metadata))    
        return jsonify(project.metadata)
    except Exception as e:
        logger().exception(str(e))
        return {"error": str(e)}, 415


@projects.post("/")
def project_add():
    schema = {
        "type": "object",
        "required": ["name", "author"],
        "properties": {
            "name": {"type": "string"},
            "author": {"type": "string"},
            "schema": {"type": "string"},
        },
    }
    try:
        logger().info(request.get_json())
        if request.is_json:
            data = request.get_json()
            validate(data, schema)

            name = data["name"]
            author = data["author"]
            schema = ""
            if "schema" in data:
                schema = data["schema"]

            project = QSAProject(name, schema)
            if project.exists():
                raise Exception("Project already exists")
            rc, err = project.create(author)
            if not rc:
                raise Exception(err)
            logger().info(rc)
            return jsonify(True), 201
        raise Exception("Request must be JSON")
    except Exception as e:
        logger().exception(str(e))
        return {"error": str(e)}, 415


@projects.delete("/<name>")
def project_del(name):
    try:
        logger().info(name)
        psql_schema = request.args.get("schema", default="public")
        project = QSAProject(name, psql_schema)

        if not project.exists():
            raise Exception("Project does not exist")
        project.remove()
        logger.info(jsonify(True))
        return jsonify(True), 201    
    except Exception as e:
        logger().exception(str(e))
        return {"error": str(e)}, 415


@projects.get("/<name>/styles")
def project_styles(name):
    try:
        logger().info(name)
        psql_schema = request.args.get("schema", default="public")
        project = QSAProject(name, psql_schema)
        if not project.exists():
            raise Exception("Project does not exist")
        logger().info(jsonify(project.styles))
        return jsonify(project.styles), 201
    except Exception as e:
        logger().exception(str(e))
        return {"error": str(e)}, 415

@projects.get("/<name>/styles/<style>")
def project_style(name, style):
    try:
        logger().info(jsonify(name=name, style=style))
        psql_schema = request.args.get("schema", default="public")
        project = QSAProject(name, psql_schema)
        if not project.exists():
            raise Exception("Project does not exist")
        infos, err = project.style(style)
        if err:
            raise Exception(err)
        logger().info(jsonify(infos))
        return jsonify(infos), 201
    except Exception as e:
        logger().exception(str(e))
        return {"error": str(e)}, 415


@projects.delete("/<name>/styles/<style>")
def project_del_style(name, style):
    psql_schema = request.args.get("schema", default="public")
    project = QSAProject(name, psql_schema)
    if project.exists():
        if style in project.styles:
            rc, msg = project.remove_style(style)
            if not rc:
                return {"error": msg}, 415
            return jsonify(rc), 201
        else:
            return {"error": "Style does not exist"}, 415
    else:
        return {"error": "Project does not exist"}, 415


@projects.post("/<name>/layers/<layer_name>/style")
def project_layer_update_style(name, layer_name):
    schema = {
        "type": "object",
        "required": ["name", "current"],
        "properties": {
            "name": {"type": "string"},
            "current": {"type": "boolean"},
        },
    }
    try:
        psql_schema = request.args.get("schema", default="public")
        project = QSAProject(name, psql_schema)
        if not project.exists():
            raise Exception("Project does not exist")
        data = request.get_json()
        
        validate(data, schema)

        current = data["current"]
        style_name = data["name"]
        rc, msg = project.layer_update_style(layer_name, style_name, current)
        if not rc:
            raise Exception(msg)
        return jsonify(True), 201
    except Exception as e:
        return {"error": str(e)}, 415


@projects.get("/<name>/layers/<layer_name>/map/url")
def project_layer_map_url(name, layer_name):
    psql_schema = request.args.get("schema", default="public")
    project = QSAProject(name, psql_schema)
    if project.exists():
        getmap = WMS.getmap_url(name, psql_schema, layer_name)
        return jsonify({"url": getmap}), 201
    else:
        return {"error": "Project does not exist"}, 415


@projects.get("/<name>/layers/<layer_name>/map")
def project_layer_map(name, layer_name):
    psql_schema = request.args.get("schema", default="public")
    project = QSAProject(name, psql_schema)
    if project.exists():
        url = WMS.getmap(name, psql_schema, layer_name)
        r = requests.get(url, stream=True)

        png = "/tmp/map.png"
        with open(png, "wb") as out_file:
            shutil.copyfileobj(r.raw, out_file)

        return send_file(png, mimetype="image/png")
    else:
        return {"error": "Project does not exist"}, 415


@projects.post("/<name>/styles")
def project_add_style(name):
    schema = {
        "type": "object",
        "required": ["name", "type", "rendering", "symbology"],
        "properties": {
            "name": {"type": "string"},
            "type": {"type": "string"},
            "symbology": {"type": "object"},
            "rendering": {"type": "object"},
        },
    }
    try:
        logger().info(request.get_json)
        psql_schema = request.args.get("schema", default="public")
        project = QSAProject(name, psql_schema)
        if not project.exists():
            raise Exception("Project does not exist")
        data = request.get_json()
        
        validate(data, schema)
        
        rc, err = project.add_style(
            data["name"],
            data["type"],
            data["symbology"],
            data["rendering"],
        )
        if not rc:
            raise Exception(err)
        logger().info(jsonify(rc))
        return jsonify(rc), 201
    except Exception as e:
        logger().exception(str(e))
        return {"error": str(e)}, 415


@projects.get("/<name>/styles/default")
def project_default_styles(name: str) -> dict:
    psql_schema = request.args.get("schema", default="public")
    project = QSAProject(name, psql_schema)
    if project.exists():
        infos = project.default_styles()
        return jsonify(infos), 201
    else:
        return {"error": "Project does not exist"}, 415


@projects.post("/<name>/styles/default")
def project_update_default_style(name):
    schema = {
        "type": "object",
        "required": ["geometry", "style"],
        "properties": {
            "geometry": {"type": "string"},
            "style": {"type": "string"},
        },
    }
    try:
        logger().info(request.get_json())
        psql_schema = request.args.get("schema", default="public")
        project = QSAProject(name, psql_schema)
        if not project.exists():
            raise Exception("Project does not exist")
        data = request.get_json()
        
        validate(data, schema)

        project.style_update(data["geometry"], data["style"])
        logger().info(jsonify(True))
        return jsonify(True), 201
    except Exception as e:
        logger().exception(str(e))
        return {"error": str(e)}, 415


@projects.get("/<name>/layers")
def project_layers(name):
    psql_schema = request.args.get("schema", default="public")
    project = QSAProject(name, psql_schema)
    if project.exists():
        return jsonify(project.layers), 201
    else:
        return {"error": "Project does not exist"}, 415


@projects.post("/<name>/layers")
def project_add_layer(name):
    schema = {
        "type": "object",
        "required": ["name", "datasource", "type"],
        "properties": {
            "name": {"type": "string"},
            "datasource": {"type": "string"},
            "crs": {"type": "number"},
            "type": {"type": "string"},
            "overview": {"type": "boolean"},
            "datetime": {"type": "string"},
        },
    }
    try:
        logger().info(request.get_json())
        psql_schema = request.args.get("schema", default="public")
        project = QSAProject(name, psql_schema)

        if not project.exists():
            raise Exception("Project does not exist")
        data = request.get_json()

        validate(data, schema)

        crs = -1
        if "crs" in data:
            crs = int(data["crs"])

        overview = False
        if "overview" in data:
            overview = data["overview"]

        datetime = None
        if "datetime" in data:
            # check format "yyyy-MM-dd HH:mm:ss"
            datetime = QDateTime.fromString(
                data["datetime"], "yyyy-MM-dd HH:mm:ss"
            )
            if not datetime.isValid():
                raise Exception("Invalid datetime")

        rc, err = project.add_layer(
            data["datasource"],
            data["type"],
            data["name"],
            crs,
            overview,
            datetime,
        )
        if not rc:
            raise Exception(err)
        logger().info(jsonify(rc))
        return jsonify(rc), 201
    except Exception as e:
        logger().exception(str(e))
        return {"error": str(e)}, 415

@projects.get("/<name>/layers/<layer_name>")
def project_info_layer(name, layer_name):
    psql_schema = request.args.get("schema", default="public")
    project = QSAProject(name, psql_schema)
    if project.exists():
        layer_infos = project.layer(layer_name)
        if layer_infos:
            return jsonify(layer_infos), 201
        else:
            return {"error": "Layer does not exist"}, 415
    else:
        return {"error": "Project does not exist"}, 415


@projects.delete("/<name>/layers/<layer_name>")
def project_del_layer(name, layer_name):
    psql_schema = request.args.get("schema", default="public")
    project = QSAProject(name, psql_schema)
    if project.exists():
        if project.layer_exists(layer_name):
            rc = project.remove_layer(layer_name)
            return jsonify(rc), 201
        else:
            return {"error": "Layer does not exist"}, 415
    else:
        return {"error": "Project does not exist"}, 415
