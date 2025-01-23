if (document.getElementById("signup")) {
    const validation = new JustValidate("#signup");

    validation
        .addField("#firstname", [
            {
                rule: "required"
            }
        ])
        .addField("#lastname", [
            {
                rule: "required"
            }
        ])
        .addField("#email", [
            {
                rule: "required"
            },
            {
                rule: "email"
            },
            {
                validator: (value) => () => {
                    return fetch("validate_email?email=" + encodeURIComponent(value))
                        .then(function(response) {
                            return response.json();
                        })
                        .then(function(json) {
                            return !json.exists;
                        });
                },
                errorMessage: "Email already in use"
            }
        ])
        .addField("#password", [
            {
                rule: "required"
            },
            {
                rule: "password"
            }
        ])
        .addField("#password_confirmation", [
            {
                validator: (value, fields) => {
                    return value === fields["#password"].elem.value;
                },
                errorMessage: "Passwords must match"
            }
        ])
        .onSuccess((event) => {
            console.log("submit")
            document.getElementById("signup").submit();
        });
}

if (document.getElementById("order")) {
    const validation = new JustValidate("#order");

    validation
        .addField("#book", [
        {
            rule: "required"
        }
        ])
        .addField("#book_pages", [
        {
            rule: "required"
        }
        ])
        .addField("#translate_from", [
        {
            rule: "required"
        }
        ])
        .addField("#translate_to", [
        {
            rule: "required"
        }
        ])
        .onSuccess((event) => {
            document.getElementById("invisible-book").value = document.getElementById("book").value;
            document.getElementById("invisible-book_pages").value = document.getElementById("book_pages").value;
            document.getElementById("invisible-translate_from").value = document.getElementById("translate_from").value;
            document.getElementById("invisible-translate_to").value = document.getElementById("translate_to").value;

            // Submit the invisible form
            document.getElementById("invisible-form").submit();
        });
}