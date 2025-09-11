import React, { useContext, useEffect, useState } from "react";
import { Context } from "../../main";
import axios from "axios";
import toast from "react-hot-toast";
import { useNavigate } from "react-router-dom";
import ResumeModal from "./ResumeModal";

const AnalysisModal = ({ open, analysis, onClose }) => (
  open ? (
    <div className="modal-overlay">
      <div className="modal-content">
        <h2>CV Evaluation</h2>
        <pre style={{ whiteSpace: 'pre-wrap' }}>{analysis}</pre>
        <button onClick={onClose}>Close</button>
      </div>
    </div>
  ) : null
);

const MyApplications = () => {
  const { user } = useContext(Context);
  const [applications, setApplications] = useState([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [resumeImageUrl, setResumeImageUrl] = useState("");
  const [analysisModalOpen, setAnalysisModalOpen] = useState(false);
  const [analysisText, setAnalysisText] = useState("");

  const { isAuthorized } = useContext(Context);
  const navigateTo = useNavigate();

  useEffect(() => {
    try {
      if (user && user.role === "Employer") {
        axios
          .get("http://localhost:4000/api/v1/application/employer/getall", {
            withCredentials: true,
          })
          .then((res) => {
            setApplications(res.data.applications);
          });
      } else {
        axios
          .get("http://localhost:4000/api/v1/application/jobseeker/getall", {
            withCredentials: true,
          })
          .then((res) => {
            setApplications(res.data.applications);
          });
      }
    } catch (error) {
      toast.error(error.response.data.message);
    }
  }, [isAuthorized]);

  if (!isAuthorized) {
    navigateTo("/");
  }

  const deleteApplication = (id) => {
    try {
      axios
        .delete(`http://localhost:4000/api/v1/application/delete/${id}`, {
          withCredentials: true,
        })
        .then((res) => {
          toast.success(res.data.message);
          setApplications((prevApplication) =>
            prevApplication.filter((application) => application._id !== id)
          );
        });
    } catch (error) {
      toast.error(error.response.data.message);
    }
  };

  const openModal = (imageUrl) => {
    setResumeImageUrl(imageUrl);
    setModalOpen(true);
  };

  const closeModal = () => {
    setModalOpen(false);
  };

  // Handler for Evaluate CV
  const handleEvaluateCV = async (application) => {
    try {
      // You may need to adjust jobId and resumeUrl based on your data model
      const payload = {
        applicationId: application._id,
        jobId: application.jobId || application.job_id,
        resumeUrl: application.resume.url
      };
      const res = await axios.post("/api/evaluate-cv", payload);
      setAnalysisText(res.data?.data?.explanation || "No analysis returned.");
      setAnalysisModalOpen(true);
    } catch (err) {
      toast.error("Evaluation failed");
    }
  };

  return (
    <section className="my_applications page">
      {user && user.role === "Job Seeker" ? (
        <div className="container">
          <h1>My Applications</h1>
          {applications.length <= 0 ? (
            <>
              {" "}
              <h4>No Applications Found</h4>{" "}
            </>
          ) : (
            applications.map((element) => {
              return (
                <JobSeekerCard
                  element={element}
                  key={element._id}
                  deleteApplication={deleteApplication}
                  openModal={openModal}
                  onEvaluateCV={() => handleEvaluateCV(element)}
                />
              );
            })
          )}
        </div>
      ) : (
        <div className="container">
          <h1>Applications From Job Seekers</h1>
          {applications.length <= 0 ? (
            <>
              <h4>No Applications Found</h4>
            </>
          ) : (
            applications.map((element) => {
              return (
                <EmployerCard
                  element={element}
                  key={element._id}
                  openModal={openModal}
                />
              );
            })
          )}
        </div>
      )}
      {modalOpen && (
        <ResumeModal imageUrl={resumeImageUrl} onClose={closeModal} />
      )}
      <AnalysisModal open={analysisModalOpen} analysis={analysisText} onClose={() => setAnalysisModalOpen(false)} />
    </section>
  );
};

export default MyApplications;

const JobSeekerCard = ({ element, deleteApplication, openModal, onEvaluateCV }) => {
  // Helper to check if file is PDF
  const isPDF = element.resume.url?.toLowerCase().endsWith('.pdf');
  return (
    <>
      <div className="job_seeker_card">
        <div className="detail">
          <p>
            <span>Name:</span> {element.name}
          </p>
          <p>
            <span>Email:</span> {element.email}
          </p>
          <p>
            <span>Phone:</span> {element.phone}
          </p>
          <p>
            <span>Address:</span> {element.address}
          </p>
          <p>
            <span>Job Desciption:</span> {element.coverLetter}
          </p>
        </div>
        <div className="resume">
          {isPDF ? (
            <a href={element.resume.url} target="_blank" rel="noopener noreferrer">
              View Resume
            </a>
          ) : (
            <img
              src={element.resume.url}
              alt="resume"
              onClick={() => openModal(element.resume.url)}
            />
          )}
        </div>
        <div className="btn_area" style={{ display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'flex-start' }}>
          <button onClick={() => deleteApplication(element._id)}>
            Delete Application
          </button>
          <button
            style={{ backgroundColor: '#007bff', color: 'white', border: 'none', padding: '8px 16px', borderRadius: '4px', cursor: 'pointer' }}
            onClick={onEvaluateCV}
          >
            Evaluate CV
          </button>
        </div>
      </div>
    </>
  );
};

const EmployerCard = ({ element, openModal }) => {
  const isPDF = element.resume.url?.toLowerCase().endsWith('.pdf');
  return (
    <>
      <div className="job_seeker_card">
        <div className="detail">
          <p>
            <span>Name:</span> {element.name}
          </p>
          <p>
            <span>Email:</span> {element.email}
          </p>
          <p>
            <span>Phone:</span> {element.phone}
          </p>
          <p>
            <span>Address:</span> {element.address}
          </p>
          <p>
            <span>Job Description:</span> {element.coverLetter}
          </p>
        </div>
        <div className="resume">
          {isPDF ? (
            <a href={element.resume.url} target="_blank" rel="noopener noreferrer">
              View Resume
            </a>
          ) : (
            <img
              src={element.resume.url}
              alt="resume"
              onClick={() => openModal(element.resume.url)}
            />
          )}
        </div>
      </div>
    </>
  );
};
