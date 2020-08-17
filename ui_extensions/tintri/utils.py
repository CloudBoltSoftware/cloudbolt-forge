import json

from .common import TintriError, TintriJSONEncoder
from .tintri import TintriBase, TintriObject


def object_to_json(obj):
    if obj == None:
        return None
    else:
        return json.dumps(obj.__dict__, cls=TintriJSONEncoder) # Use __dict__ to avoid not JSON serializable error

def map_to_object(m, cls):
    def __getobjecttype(cls, varname):
        from .tintri import  TintriObject

        if '_property_map' in dir(cls):
            if varname in cls._property_map.keys():
                return cls._property_map[varname]
        return TintriObject

    if type(m) == dict:
        o = cls()

        ignoresetattr = None
        if hasattr(o, '_ignoresetattr'):
            ignoresetattr = o._ignoresetattr
            o._ignoresetattr = True

        for k in m.keys():
            cls2 = __getobjecttype(cls, k)
            setattr(o, k, map_to_object(m[k], cls2))

        if ignoresetattr:
            o._ignoresetattr = ignoresetattr

        return o
    elif type(m) == list:
        objects = []
        for obj in m:
            objects.append(map_to_object(obj, cls))
        return objects
    else:
        return m


def convert_to_camel_case(name, capitalize_first_letter=True):
    new_name = "".join(item.title() for item in name.split('_'))
    if capitalize_first_letter:
        return new_name
    else:
        return new_name[0].lower() + new_name[1:]

# Use this decorator for all apis. For usage, please see get_vm
# Anytime resource is added/updated, keep the decorated apis consistent
def api(func=None, filter_class=None, target="all", version="all"):
    def is_plural(func):
        if not func.func_name.endswith('s'):
            return False

        resource = "_".join(func.func_name.split("_")[1:])
        resource = convert_to_camel_case(resource)
        if resource not in func.func_globals:
            return True
        
        resource_class = func.func_globals[resource]
        if hasattr(resource_class, '_ignore_plural') and resource_class._ignore_plural:
            return False

        return True

    def get_resource_class_from_func_name(func_name, func):
        """Figure out resource class name using function name"""
        if func_name in ["get_appliance_timezones"]:
            return None
        obj_str = convert_to_camel_case("_".join(func_name.split("_")[1:]))
        return func.func_globals[obj_str]
    
    def get_op(func):
        if func.func_name.startswith('get'):
            if is_plural(func):
                return 'get_all', func.func_name[:-1]
            else:
                return 'get_one', func.func_name
        elif func.func_name.startswith('create'):
            return 'create', func.func_name
        elif func.func_name.startswith('delete'):
            return 'delete', func.func_name
        elif func.func_name.startswith('update'):
            return 'update', func.func_name
        else:
            raise TintriError("Unknown API operation: %s" % func.func_name)

    def wrap(func):
        def verify_filter(api_filter, filter_class):
            if filter_class and not type(api_filter) is dict and not type(api_filter) is filter_class:
                raise Exception("Invalid filter spec, filter should be a map or of type %s" % str(filter_class))   

        def verify_target(api_target, tintri_obj):
            if api_target.lower() == "tgc" and tintri_obj.is_vmstore():
                raise TintriError("API applicable to TGC only")
            if api_target.lower() == "vmstore" and tintri_obj.is_tgc():
                raise TintriError("API applicable to VMstore only")
        
        def verify_version(api_version, tintri_obj):
            if version.lower() != "all" and not version in tintri_obj.version.supportedVersionSet:
                raise TintriError("Unsupported API, please check API minimum version")

        def is_generated_function(func, tintri_obj):
            if len(tintri_obj._generated_function.func_code.co_code) == len(tintri_obj._generated_function_with_doc.func_code.co_code):
                if len(func.func_code.co_code) == len(tintri_obj._generated_function.func_code.co_code):
                    return func.func_code.co_code == tintri_obj._generated_function.func_code.co_code or func.func_code.co_code == tintri_obj._generated_function_with_doc.func_code.co_code
                return False
            else:
                if len(func.func_code.co_code) == len(tintri_obj._generated_function.func_code.co_code):
                    return func.func_code.co_code == tintri_obj._generated_functiontion.func_code.co_code
                elif len(func.func_code.co_code) == len(tintri_obj._generated_function_with_doc.func_code.co_code):
                    return func.func_code.co_code == tintri_obj._generated_function_with_doc.func_code.co_code
                return False

        def is_property_updateable(key, value, data):
            ret = False
            if value is not None and key != 'id' and key != 'uuid' and key != 'typeId':
                ret = True
                if hasattr(type(data), '_id_fields') and key in type(data)._id_fields:
                    ret = False
            return ret

        @wraps(func)
        def wrapped(*args, **kwargs):
            data = None
            query_params = {}
            filters = None
            path_params = []
            response_class = None

            tintri_obj = args[0]
            
            # verify target and version before proceeding
            verify_target(target, tintri_obj)
            verify_version(version, tintri_obj)

            if not is_generated_function(func, tintri_obj):
                return func(*args, **kwargs)
            
            if 'filters' in kwargs:
                verify_filter(kwargs['filters'], filter_class)
                filters = kwargs['filters']
                del kwargs['filters']

            if 'query_params' in kwargs:
                query_params = kwargs['query_params']
                del kwargs['query_params']
                
            op_type, actual_func_name = get_op(func)
            resource_class = get_resource_class_from_func_name(actual_func_name, func)
            request_class = resource_class
            if resource_class._is_paginated:
                response_class = resource_class

            if len(args) > 1:
                path_params = list(args[1:])
            if op_type == "create":
                # first argument is data
                data = path_params.pop(0)
            elif op_type == "update":
                '''
                first argument is considered as data
                1. If data is not None, construct Request from data
                2. If data is None, Request is not None, use Request as data
                3. If data is None, and Request is None, construct Request from kwargs
                '''
                if len(path_params) == 0:
                    raise TypeError("Incorrect usage of API, please provide either updated object or Request object or set properties")
                data = path_params.pop(0)
                if data is None:
                    if 'request' in kwargs and kwargs['request']:
                        data = kwargs['request']
                    else:
                        if len(kwargs):
                            data = _get_request_object(kwargs, [], resource_class)
                        else:
                            # obj, Request and kwargs are None
                            raise TintriError("Incorrect usage of API, please provide either updated object or Request object or set properties")
                else:
                    if 'request' in kwargs:
                        # construct Request from data
                        request = Request()
                        # prepare request
                        request.objectsWithNewValues = [data]
                        request.propertiesToBeUpdated = []
                        for key, value in data.__dict__.iteritems():
                            # ignore None, ID and UUID keys; ignore name key for FileShare
                            if is_property_updateable(key, value, data):
                                request.propertiesToBeUpdated.append(key)
                        data = request
                dump_object(data, logger=tintri_obj.logger)

            if op_type.lower() == "get_one":
                return tintri_obj._get_one(path_params=path_params, query_params=query_params, filters=filters, request_class=request_class, response_class=response_class)
            elif op_type.lower() == "get_all":
                return tintri_obj._get_all(path_params=path_params, query_params=query_params, filters=filters, request_class=request_class, response_class=response_class)
            elif op_type.lower() == "create":
                return tintri_obj._create(data, path_params=path_params, query_params=query_params, filters=filters, request_class=request_class, response_class=response_class)
            elif op_type.lower() == "delete":
                return tintri_obj._delete(path_params=path_params, query_params=query_params, filters=filters, request_class=request_class, response_class=response_class)
            elif op_type.lower() == "update":
                return tintri_obj._update(data, path_params=path_params, query_params=query_params, filters=filters, request_class=request_class, response_class=response_class)
            else:
                raise TintriError("Unrecognized request op_type %s" % op_type)
        return wrapped

    def get_method_doc_string(func):

        def get_param_desc(param):
            param_desc = ''
            if param.endswith('id'):
                for word in param.split("_")[:-1]:
                    param_desc = param_desc + word.capitalize()
                    param_desc = param_desc + ' '
                param_desc = param_desc + "Object's UUID"
            else:
                for word in param.split("_"):
                    param_desc = param_desc + word.capitalize()
                    param_desc = param_desc + ' '
            return param_desc

        op_type, actual_func_name = get_op(func)
        resource_class = get_resource_class_from_func_name(actual_func_name, func)
        doc_string = "Invalid doc string."

        # Get text based on API verb.
        if op_type == 'get_all':
            doc_string = "Gets all " + resource_class.__name__ + "s, and returns them in a Page object."
        elif op_type == 'get_one':
            doc_string = "Gets a specific " + resource_class.__name__ + " object by its ID."
        elif op_type == 'create':
            doc_string = "Creates %s " % ("an" if resource_class.__name__[0] in 'aeiouAEIOU' else "a") + resource_class.__name__ + " object." 
        elif op_type == 'update':
            doc_string = "Updates the " + resource_class.__name__ + " object specified by its ID."
        elif op_type == 'delete':
            doc_string = "Deletes the " + resource_class.__name__ + " object specified by its ID."

        # Get which Tintri server is supported.
        doc_string += "\n\n**Supported on:** "
        if target == "tgc":
            doc_string += "TGC"
        elif target == "vmstore":
            doc_string += "VMstore"
        elif target == "all":
            doc_string += "VMstore and TGC"
        if version == "all":
            doc_string += " (all versions)"
        else:
            doc_string+= " (since %s)" % version

        # Get input arguments.
        obj_name = ""
        param_l = inspect.getargspec(func)[0]
        param_l.remove("self")
        if param_l:
            doc_string += "\n\nArgs:"
        for param in param_l:
            if param == "filters":
                doc_string += "\n\tfilters (dict or `%s`): Filter Spec object" % filter_class.__name__
            elif param == "query_params":
                doc_string += "\n\tquery_params (dict): Specify query parameters as a dictionary"
            elif param == "request":
                doc_string += "\n\trequest (`Request`<`%s`>): %s request" % (resource_class.__name__, resource_class.__name__)
            else:
                if param == 'obj':
                    # Special case for create_acl.
                    if actual_func_name == "create_acl":
                        obj_name = "Ace"
                    else:
                        obj_name = resource_class.__name__
                    doc_string += "\n\tobj (`%s`): An instance of %s." % (obj_name, resource_class.__name__)
                else:
                    doc_string += "\n\t"
                    doc_string += param + " (str): "
                    doc_string += get_param_desc(param)

        if not param_l:
            doc_string += "\n\n"
        
        # Get return output.
        if op_type == 'get_all':
            if resource_class._is_paginated:
                doc_string = doc_string + "\nReturns:\n\t`Page`: Paginated `" + resource_class.__name__ + "` objects."
            else:
                doc_string = doc_string + "\nReturns:\n\tList[`" + resource_class.__name__ + "`]: A list of " + resource_class.__name__ + " objects."
        elif op_type == 'get_one':
            doc_string = doc_string + "\nReturns:\n\t`" + resource_class.__name__ + "`: The " + resource_class.__name__ + " with the specified ID."
        elif (op_type == 'create') and (len(param_l) >= 1) and (param_l[0] == 'obj'):
            doc_string += "\nReturns:\n\t`" + obj_name + "`: The " + obj_name + " object created."

        return doc_string

    if func is None:
        def decorator(func):
            if not func.__doc__ and not 'internal' in func.__module__:
                func.__doc__ = get_method_doc_string(func)
            TintriBase.method_registry[func.func_name] = func
            return wrap(func)
        return decorator

    if not func.__doc__ and not 'internal' in func.__module__:
        func.__doc__ = get_method_doc_string(func)
    TintriBase.method_registry[func.func_name] = func

    return wrap(func)
