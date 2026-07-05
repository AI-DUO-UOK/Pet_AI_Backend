def route_prediction(app, animal, disease_type, tensor):

    if animal == "dog" and disease_type == "skin":
        model, classes = app.state.dog_skin
    elif animal == "dog" and disease_type == "eye":
        model, classes = app.state.dog_eye
    elif animal == "cat" and disease_type == "skin":
        model, classes = app.state.cat_skin
    else:
        return {"error": "Invalid input"}

    from services.predictor import predict
    return predict(model, classes, tensor)