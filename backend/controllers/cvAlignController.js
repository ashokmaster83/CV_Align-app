import axios from 'axios';

// FastAPI service base URL
const FASTAPI_URL = 'http://localhost:8000';

// Rank CVs for recruiters
export const rankCVs = async (req, res) => {
    try {
        const { job_description, cvs } = req.body;
        const response = await axios.post(`${FASTAPI_URL}/rank-cvs`, {
            job_description,
            cvs
        });
        res.json(response.data);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
};

// Analyse CV for job seekers
export const analyseCV = async (req, res) => {
    try {
        const { job_description, cv } = req.body;
        const response = await axios.post(`${FASTAPI_URL}/analyse-cv`, {
            job_description,
            cv
        });
        res.json(response.data);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
};
