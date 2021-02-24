export async function fetch_via_post(url, rh_id, csrfToken) {
    const response = await fetch(url, {
        body: JSON.stringify({ "rh_id": rh_id }),
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrfToken
        },
        method: "post"
    });
    return await response.json();
};