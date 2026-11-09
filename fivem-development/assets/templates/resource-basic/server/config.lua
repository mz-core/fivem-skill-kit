-- Server-only: players never receive this file. Anything that decides outcomes lives here.
ServerConfig = {
    -- Catalog of valid interaction points. The client may only name one of these keys.
    Points = {
        office = { coords = vector3(215.76, -810.12, 30.73), radius = 4.0 },
    },
    CooldownSeconds = 3,
    RequireAce = true,
    Ace = '{{RESOURCE_NAME}}.use',
}
